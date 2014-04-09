#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
pyScss, a Scss compiler for Python

@author     German M. Bravo (Kronuz) <german.mb@gmail.com>
@version    1.2.0 alpha
@see        https://github.com/Kronuz/pyScss
@copyright  (c) 2012-2013 German M. Bravo (Kronuz)
@license    MIT License
            http://www.opensource.org/licenses/mit-license.php

pyScss compiles Scss, a superset of CSS that is more powerful, elegant and
easier to maintain than plain-vanilla CSS. The library acts as a CSS source code
preprocesor which allows you to use variables, nested rules, mixins, andhave
inheritance of rules, all with a CSS-compatible syntax which the preprocessor
then compiles to standard CSS.

Scss, as an extension of CSS, helps keep large stylesheets well-organized. It
borrows concepts and functionality from projects such as OOCSS and other similar
frameworks like as Sass. It's build on top of the original PHP xCSS codebase
structure but it's been completely rewritten, many bugs have been fixed and it
has been extensively extended to support almost the full range of Sass' Scss
syntax and functionality.

Bits of code in pyScss come from various projects:
Compass:
    (c) 2009 Christopher M. Eppstein
    http://compass-style.org/
Sass:
    (c) 2006-2009 Hampton Catlin and Nathan Weizenbaum
    http://sass-lang.com/
xCSS:
    (c) 2010 Anton Pawlik
    http://xcss.antpaw.org/docs/

"""
from __future__ import absolute_import
from __future__ import print_function

from scss.scss_meta import BUILD_INFO, PROJECT, VERSION, REVISION, URL, AUTHOR, AUTHOR_EMAIL, LICENSE

__project__ = PROJECT
__version__ = VERSION
__author__ = AUTHOR + ' <' + AUTHOR_EMAIL + '>'
__license__ = LICENSE


from collections import defaultdict
import glob
from itertools import product
import logging
import os.path
import re
import sys

import six

from scss import config
from scss.cssdefs import (
    SEPARATOR,
    _ml_comment_re, _sl_comment_re,
    _escape_chars_re,
    _spaces_re, _expand_rules_space_re, _collapse_properties_space_re,
    _strings_re, _prop_split_re,
)
from scss.errors import SassError
from scss.expression import Calculator
from scss.functions import ALL_BUILTINS_LIBRARY
from scss.functions.compass.sprites import sprite_map
from scss.rule import Namespace, SassRule, UnparsedBlock
from scss.types import Boolean, List, Null, Number, String, Undefined
from scss.util import dequote, normalize_var, print_timing  # profile

log = logging.getLogger(__name__)

################################################################################
# Load C acceleration modules
locate_blocks = None
try:
    from scss._speedups import locate_blocks
except ImportError:
    import warnings
    warnings.warn(
        "Scanning acceleration disabled (_speedups not found)!",
        RuntimeWarning
        )
    from scss._native import locate_blocks

################################################################################


_safe_strings = {
    '^doubleslash^': '//',
    '^bigcopen^': '/*',
    '^bigcclose^': '*/',
    '^doubledot^': ':',
    '^semicolon^': ';',
    '^curlybracketopen^': '{',
    '^curlybracketclosed^': '}',
}
_reverse_safe_strings = dict((v, k) for k, v in _safe_strings.items())
_safe_strings_re = re.compile('|'.join(map(re.escape, _safe_strings)))
_reverse_safe_strings_re = re.compile('|'.join(map(re.escape, _reverse_safe_strings)))

_default_scss_vars = {
    '$BUILD-INFO': String.unquoted(BUILD_INFO),
    '$PROJECT': String.unquoted(PROJECT),
    '$VERSION': String.unquoted(VERSION),
    '$REVISION': String.unquoted(REVISION),
    '$URL': String.unquoted(URL),
    '$AUTHOR': String.unquoted(AUTHOR),
    '$AUTHOR-EMAIL': String.unquoted(AUTHOR_EMAIL),
    '$LICENSE': String.unquoted(LICENSE),

    # unsafe chars will be hidden as vars
    '$--doubleslash': String.unquoted('//'),
    '$--bigcopen': String.unquoted('/*'),
    '$--bigcclose': String.unquoted('*/'),
    '$--doubledot': String.unquoted(':'),
    '$--semicolon': String.unquoted(';'),
    '$--curlybracketopen': String.unquoted('{'),
    '$--curlybracketclosed': String.unquoted('}'),

    # shortcuts (it's "a hidden feature" for now)
    'bg:': String.unquoted('background:'),
    'bgc:': String.unquoted('background-color:'),
}


################################################################################


class SourceFile(object):
    def __init__(self, filename, contents, parent_dir='.', is_string=False, is_sass=None, line_numbers=True, line_strip=True):
        self.filename = filename
        self.sass = filename.endswith('.sass') if is_sass is None else is_sass
        self.line_numbers = line_numbers
        self.line_strip = line_strip
        self.contents = self.prepare_source(contents)
        self.parent_dir = os.path.realpath(parent_dir)
        self.is_string = is_string

    def __repr__(self):
        return "<SourceFile '%s' at 0x%x>" % (
            self.filename,
            id(self),
        )

    @classmethod
    def from_filename(cls, fn, filename=None, is_sass=None, line_numbers=True):
        if filename is None:
            _, filename = os.path.split(fn)

        with open(fn) as f:
            contents = f.read()

        return cls(filename, contents, is_sass=is_sass, line_numbers=line_numbers)

    @classmethod
    def from_string(cls, string, filename=None, is_sass=None, line_numbers=True):
        if filename is None:
            filename = "<string %r...>" % string[:50]

        return cls(filename, string, is_string=True, is_sass=is_sass, line_numbers=line_numbers)

    def parse_scss_line(self, line_no, line, state):
        ret = ''

        if line is None:
            line = ''

        line = state['line_buffer'] + line.rstrip()  # remove EOL character

        if line and line[-1] == '\\':
            state['line_buffer'] = line[:-1]
            return ''
        else:
            state['line_buffer'] = ''

        output = state['prev_line']
        if self.line_strip:
            output = output.strip()
        output_line_no = state['prev_line_no']

        state['prev_line'] = line
        state['prev_line_no'] = line_no

        if output:
            if self.line_numbers:
                output = str(output_line_no + 1) + SEPARATOR + output
            output += '\n'
            ret += output

        return ret

    def parse_sass_line(self, line_no, line, state):
        ret = ''

        if line is None:
            line = ''

        line = state['line_buffer'] + line.rstrip()  # remove EOL character

        if line and line[-1] == '\\':
            state['line_buffer'] = line[:-1]
            return ret
        else:
            state['line_buffer'] = ''

        indent = len(line) - len(line.lstrip())

        # make sure we support multi-space indent as long as indent is consistent
        if indent and not state['indent_marker']:
            state['indent_marker'] = indent

        if state['indent_marker']:
            indent /= state['indent_marker']

        if indent == state['prev_indent']:
            # same indentation as previous line
            if state['prev_line']:
                state['prev_line'] += ';'
        elif indent > state['prev_indent']:
            # new indentation is greater than previous, we just entered a new block
            state['prev_line'] += ' {'
            state['nested_blocks'] += 1
        else:
            # indentation is reset, we exited a block
            block_diff = state['prev_indent'] - indent
            if state['prev_line']:
                state['prev_line'] += ';'
            state['prev_line'] += ' }' * block_diff
            state['nested_blocks'] -= block_diff

        output = state['prev_line']
        if self.line_strip:
            output = output.strip()
        output_line_no = state['prev_line_no']

        state['prev_indent'] = indent
        state['prev_line'] = line
        state['prev_line_no'] = line_no

        if output:
            if self.line_numbers:
                output = str(output_line_no + 1) + SEPARATOR + output
            output += '\n'
            ret += output
        return ret

    def prepare_source(self, codestr, sass=False):
        # Decorate lines with their line numbers and a delimiting NUL and remove empty lines
        state = {
            'line_buffer': '',
            'prev_line': '',
            'prev_line_no': 0,
            'prev_indent': 0,
            'nested_blocks': 0,
            'indent_marker': 0,
        }
        if self.sass:
            parse_line = self.parse_sass_line
        else:
            parse_line = self.parse_scss_line
        _codestr = codestr
        codestr = ''
        for line_no, line in enumerate(_codestr.splitlines()):
            codestr += parse_line(line_no, line, state)
        codestr += parse_line(None, None, state)  # parse the last line stored in prev_line buffer

        # protects codestr: "..." strings
        codestr = _strings_re.sub(lambda m: _reverse_safe_strings_re.sub(lambda n: _reverse_safe_strings[n.group(0)], m.group(0)), codestr)

        # removes multiple line comments
        codestr = _ml_comment_re.sub('', codestr)

        # removes inline comments, but not :// (protocol)
        codestr = _sl_comment_re.sub('', codestr)

        codestr = _safe_strings_re.sub(lambda m: _safe_strings[m.group(0)], codestr)

        # expand the space in rules
        codestr = _expand_rules_space_re.sub(' {', codestr)

        # collapse the space in properties blocks
        codestr = _collapse_properties_space_re.sub(r'\1{', codestr)

        return codestr


class Scss(object):
    def __init__(self,
            scss_vars=None, scss_opts=None, scss_files=None, super_selector=None,
            live_errors=False, library=ALL_BUILTINS_LIBRARY, func_registry=None, search_paths=None):

        if super_selector:
            self.super_selector = super_selector + ' '
        else:
            self.super_selector = ''

        self._scss_vars = {}
        if scss_vars:
            calculator = Calculator()
            for var_name, value in scss_vars.items():
                if isinstance(value, six.string_types):
                    scss_value = calculator.evaluate_expression(value)
                    if scss_value is None:
                        # TODO warning?
                        scss_value = String.unquoted(value)
                else:
                    scss_value = value
                self._scss_vars[var_name] = scss_value

        self._scss_opts = scss_opts
        self._scss_files = scss_files
        # NOTE: func_registry is backwards-compatibility for only one user and
        # has never existed in a real release
        self._library = func_registry or library
        self._search_paths = search_paths

        # If true, swallow compile errors and embed them in the output instead
        self.live_errors = live_errors

        self.reset()

    def get_scss_constants(self):
        scss_vars = self.root_namespace.variables
        return dict((k, v) for k, v in scss_vars.items() if k and (not k.startswith('$') or k.startswith('$') and k[1].isupper()))

    def get_scss_vars(self):
        scss_vars = self.root_namespace.variables
        return dict((k, v) for k, v in scss_vars.items() if k and not (not k.startswith('$') or k.startswith('$') and k[1].isupper()))

    def reset(self, input_scss=None):
        # Initialize
        self.scss_vars = _default_scss_vars.copy()
        if self._scss_vars is not None:
            self.scss_vars.update(self._scss_vars)

        self.scss_opts = self._scss_opts.copy() if self._scss_opts else {}

        self.root_namespace = Namespace(variables=self.scss_vars, functions=self._library)

        # Figure out search paths.  Fall back from provided explicitly to
        # defined globally to just searching the current directory
        self.search_paths = ['.']
        if self._search_paths is not None:
            assert not isinstance(self._search_paths, six.string_types), \
                "`search_paths` should be an iterable, not a string"
            self.search_paths.extend(self._search_paths)
        else:
            if config.LOAD_PATHS:
                if isinstance(config.LOAD_PATHS, six.string_types):
                    # Back-compat: allow comma-delimited
                    self.search_paths.extend(config.LOAD_PATHS.split(','))
                else:
                    self.search_paths.extend(config.LOAD_PATHS)

            self.search_paths.extend(self.scss_opts.get('load_paths', []))

        self.source_files = []
        self.source_file_index = {}
        if self._scss_files is not None:
            for name, contents in list(self._scss_files.items()):
                if name in self.source_file_index:
                    raise KeyError("Duplicate filename %r" % name)
                source_file = SourceFile(name, contents)
                self.source_files.append(source_file)
                self.source_file_index[name] = source_file

        self.rules = []

    #@profile
    #@print_timing(2)
    def Compilation(self, scss_string=None, scss_file=None, super_selector=None, filename=None, is_sass=None, line_numbers=True):
        if super_selector:
            self.super_selector = super_selector + ' '
        self.reset()

        source_file = None
        if scss_string is not None:
            source_file = SourceFile.from_string(scss_string, filename, is_sass, line_numbers)
        elif scss_file is not None:
            source_file = SourceFile.from_filename(scss_file, filename, is_sass, line_numbers)

        if source_file is not None:
            # Clear the existing list of files
            self.source_files = []
            self.source_file_index = dict()

            self.source_files.append(source_file)
            self.source_file_index[source_file.filename] = source_file

        # this will compile and manage rule: child objects inside of a node
        self.parse_children()

        # this will manage @extends
        self.apply_extends()

        rules_by_file, css_files = self.parse_properties()

        all_rules = 0
        all_selectors = 0
        exceeded = ''
        final_cont = ''
        files = len(css_files)
        for source_file in css_files:
            rules = rules_by_file[source_file]
            fcont, total_rules, total_selectors = self.create_css(rules)
            all_rules += total_rules
            all_selectors += total_selectors
            if not exceeded and all_selectors > 4095:
                exceeded = " (IE exceeded!)"
                log.error("Maximum number of supported selectors in Internet Explorer (4095) exceeded!")
            if files > 1 and self.scss_opts.get('debug_info', False):
                if source_file.is_string:
                    final_cont += "/* %s %s generated add up to a total of %s %s accumulated%s */\n" % (
                        total_selectors,
                        'selector' if total_selectors == 1 else 'selectors',
                        all_selectors,
                        'selector' if all_selectors == 1 else 'selectors',
                        exceeded)
                else:
                    final_cont += "/* %s %s generated from '%s' add up to a total of %s %s accumulated%s */\n" % (
                        total_selectors,
                        'selector' if total_selectors == 1 else 'selectors',
                        source_file.filename,
                        all_selectors,
                        'selector' if all_selectors == 1 else 'selectors',
                        exceeded)
            final_cont += fcont

        return final_cont

    def compile(self, *args, **kwargs):
        try:
            return self.Compilation(*args, **kwargs)
        except SassError as e:
            if self.live_errors:
                # TODO should this setting also capture and display warnings?
                return e.to_css()
            else:
                raise

    def parse_selectors(self, raw_selectors):
        """
        Parses out the old xCSS "foo extends bar" syntax.

        Returns a 2-tuple: a set of selectors, and a set of extended selectors.
        """
        # Fix tabs and spaces in selectors
        raw_selectors = _spaces_re.sub(' ', raw_selectors)

        import re

        from scss.selector import Selector

        parts = re.split(r'\s+extends\s+', raw_selectors, 1)
        if len(parts) > 1:
            unparsed_selectors, unsplit_parents = parts
            # Multiple `extends` are delimited by `&`
            unparsed_parents = unsplit_parents.split('&')
        else:
            unparsed_selectors, = parts
            unparsed_parents = ()

        selectors = Selector.parse_many(unparsed_selectors)
        parents = [Selector.parse_one(parent) for parent in unparsed_parents]

        return selectors, parents

    @print_timing(3)
    def parse_children(self, scope=None):
        children = []
        root_namespace = self.root_namespace
        for source_file in self.source_files:
            rule = SassRule(
                source_file=source_file,

                unparsed_contents=source_file.contents,
                namespace=root_namespace,
                options=self.scss_opts,
            )
            self.rules.append(rule)
            children.append(rule)

        for rule in children:
            self.manage_children(rule, scope)

        if self.scss_opts.get('warn_unused'):
            for name, file_and_line in root_namespace.unused_imports():
                log.warn("Unused @import: '%s' (%s)", name, file_and_line)

    @print_timing(4)
    def manage_children(self, rule, scope):
        try:
            self._manage_children_impl(rule, scope)
        except SassReturn:
            raise
        except SassError as e:
            e.add_rule(rule)
            raise
        except Exception as e:
            raise SassError(e, rule=rule)

    def _manage_children_impl(self, rule, scope):
        calculator = Calculator(rule.namespace)

        for c_lineno, c_property, c_codestr in locate_blocks(rule.unparsed_contents):
            block = UnparsedBlock(rule, c_lineno, c_property, c_codestr)

            if block.is_atrule:
                code = block.directive
                code = code.lower()
                if code == '@warn':
                    value = calculator.calculate(block.argument)
                    log.warn(repr(value))
                elif code == '@print':
                    value = calculator.calculate(block.argument)
                    sys.stderr.write("%s\n" % value)
                elif code == '@raw':
                    value = calculator.calculate(block.argument)
                    sys.stderr.write("%s\n" % repr(value))
                elif code == '@dump_context':
                    sys.stderr.write("%s\n" % repr(rule.namespace._variables))
                elif code == '@dump_functions':
                    sys.stderr.write("%s\n" % repr(rule.namespace._functions))
                elif code == '@dump_mixins':
                    sys.stderr.write("%s\n" % repr(rule.namespace._mixins))
                elif code == '@dump_imports':
                    sys.stderr.write("%s\n" % repr(rule.namespace._imports))
                elif code == '@dump_options':
                    sys.stderr.write("%s\n" % repr(rule.options))
                elif code == '@debug':
                    setting = block.argument.strip()
                    if setting.lower() in ('1', 'true', 't', 'yes', 'y', 'on'):
                        setting = True
                    elif setting.lower() in ('0', 'false', 'f', 'no', 'n', 'off', 'undefined'):
                        setting = False
                    config.DEBUG = setting
                    log.info("Debug mode is %s", 'On' if config.DEBUG else 'Off')
                elif code == '@option':
                    self._settle_options(rule, scope, block)
                elif code == '@content':
                    self._do_content(rule, scope, block)
                elif code == '@import':
                    self._do_import(rule, scope, block)
                elif code == '@extend':
                    from scss.selector import Selector
                    selectors = calculator.apply_vars(block.argument)
                    # XXX this no longer handles `&`, which is from xcss
                    rule.extends_selectors.extend(Selector.parse_many(selectors))
                    #rule.extends_selectors.update(p.strip() for p in selectors.replace(',', '&').split('&'))
                    #rule.extends_selectors.discard('')
                elif code == '@return':
                    # TODO should assert this only happens within a @function
                    ret = calculator.calculate(block.argument)
                    raise SassReturn(ret)
                elif code == '@include':
                    self._do_include(rule, scope, block)
                elif code in ('@mixin', '@function'):
                    self._do_functions(rule, scope, block)
                elif code in ('@if', '@else if'):
                    self._do_if(rule, scope, block)
                elif code == '@else':
                    self._do_else(rule, scope, block)
                elif code == '@for':
                    self._do_for(rule, scope, block)
                elif code == '@each':
                    self._do_each(rule, scope, block)
                elif code == '@while':
                    self._do_while(rule, scope, block)
                elif code in ('@variables', '@vars'):
                    self._get_variables(rule, scope, block)
                elif block.unparsed_contents is None:
                    rule.properties.append((block.prop, None))
                elif scope is None:  # needs to have no scope to crawl down the nested rules
                    self._nest_at_rules(rule, scope, block)
            ####################################################################
            # Properties
            elif block.unparsed_contents is None:
                self._get_properties(rule, scope, block)
            # Nested properties
            elif block.is_scope:
                if block.header.unscoped_value:
                    # Possibly deal with default unscoped value
                    self._get_properties(rule, scope, block)

                rule.unparsed_contents = block.unparsed_contents
                subscope = (scope or '') + block.header.scope + '-'
                self.manage_children(rule, subscope)
            ####################################################################
            # Nested rules
            elif scope is None:  # needs to have no scope to crawl down the nested rules
                self._nest_rules(rule, scope, block)

    @print_timing(10)
    def _settle_options(self, rule, scope, block):
        for option in block.argument.split(','):
            option, value = (option.split(':', 1) + [''])[:2]
            option = option.strip().lower()
            value = value.strip()
            if option:
                if value.lower() in ('1', 'true', 't', 'yes', 'y', 'on'):
                    value = True
                elif value.lower() in ('0', 'false', 'f', 'no', 'n', 'off', 'undefined'):
                    value = False
                option = option.replace('-', '_')
                if option == 'compress':
                    option = 'style'
                    log.warn("The option 'compress' is deprecated. Please use 'style' instead.")
                rule.options[option] = value

    def _get_funct_def(self, rule, calculator, argument):
        funct, lpar, argstr = argument.partition('(')
        funct = calculator.do_glob_math(funct)
        funct = normalize_var(funct.strip())
        argstr = argstr.strip()

        # Parse arguments with the argspec rule
        if lpar:
            if not argstr.endswith(')'):
                raise SyntaxError("Expected ')', found end of line for %s (%s)" % (funct, rule.file_and_line))
            argstr = argstr[:-1].strip()
        else:
            # Whoops, no parens at all.  That's like calling with no arguments.
            argstr = ''

        argstr = calculator.do_glob_math(argstr)
        argspec_node = calculator.parse_expression(argstr, target='goal_argspec')
        return funct, argspec_node

    def _populate_namespace_from_call(self, name, callee_namespace, mixin, args, kwargs):
        # Mutation protection
        args = list(args)
        kwargs = dict(kwargs)

        #m_params = mixin[0]
        #m_defaults = mixin[1]
        #m_codestr = mixin[2]
        pristine_callee_namespace = mixin[3]
        callee_argspec = mixin[4]
        import_key = mixin[5]

        callee_calculator = Calculator(callee_namespace)

        # Populate the mixin/function's namespace with its arguments
        for var_name, node in callee_argspec.iter_def_argspec():
            if args:
                # If there are positional arguments left, use the first
                value = args.pop(0)
            elif var_name in kwargs:
                # Try keyword arguments
                value = kwargs.pop(var_name)
            elif node is not None:
                # OK, there's a default argument; try that
                # DEVIATION: this allows argument defaults to refer to earlier
                # argument values
                value = node.evaluate(callee_calculator, divide=True)
            else:
                # TODO this should raise
                value = Undefined()

            callee_namespace.set_variable(var_name, value, local_only=True)

        if callee_argspec.slurp:
            # Slurpy var gets whatever is left
            callee_namespace.set_variable(
                callee_argspec.slurp.name,
                List(args, use_comma=True))
            args = []
        elif callee_argspec.inject:
            # Callee namespace gets all the extra kwargs whether declared or
            # not
            for var_name, value in kwargs.items():
                callee_namespace.set_variable(var_name, value, local_only=True)
            kwargs = {}

        # TODO would be nice to say where the mixin/function came from
        if kwargs:
            raise NameError("%s has no such argument %s" % (name, kwargs.keys()[0]))

        if args:
            raise NameError("%s received extra arguments: %r" % (name, args))

        pristine_callee_namespace.use_import(import_key)
        return callee_namespace

    @print_timing(10)
    def _do_functions(self, rule, scope, block):
        """
        Implements @mixin and @function
        """
        if not block.argument:
            raise SyntaxError("%s requires a function name (%s)" % (block.directive, rule.file_and_line))

        calculator = Calculator(rule.namespace)
        funct, argspec_node = self._get_funct_def(rule, calculator, block.argument)

        defaults = {}
        new_params = []

        for var_name, default in argspec_node.iter_def_argspec():
            new_params.append(var_name)
            if default is not None:
                defaults[var_name] = default

        mixin = [rule.source_file, block.lineno, block.unparsed_contents, rule.namespace, argspec_node, rule.import_key]
        if block.directive == '@function':
            def _call(mixin):
                def __call(namespace, *args, **kwargs):
                    source_file = mixin[0]
                    lineno = mixin[1]
                    m_codestr = mixin[2]
                    pristine_callee_namespace = mixin[3]
                    callee_namespace = pristine_callee_namespace.derive()

                    # TODO CallOp converts Sass names to Python names, so we
                    # have to convert them back to Sass names.  would be nice
                    # to avoid this back-and-forth somehow
                    kwargs = dict(
                        (normalize_var('$' + key), value)
                        for (key, value) in kwargs.items())

                    self._populate_namespace_from_call(
                        "Function {0}".format(funct),
                        callee_namespace, mixin, args, kwargs)

                    _rule = SassRule(
                        source_file=source_file,
                        lineno=lineno,
                        unparsed_contents=m_codestr,
                        namespace=callee_namespace,

                        # rule
                        import_key=rule.import_key,
                        options=rule.options,
                        properties=rule.properties,
                        extends_selectors=rule.extends_selectors,
                        ancestry=rule.ancestry,
                        nested=rule.nested,
                    )
                    try:
                        self.manage_children(_rule, scope)
                    except SassReturn as e:
                        return e.retval
                    else:
                        return Null()
                return __call
            _mixin = _call(mixin)
            _mixin.mixin = mixin
            mixin = _mixin

        if block.directive == '@mixin':
            add = rule.namespace.set_mixin
        elif block.directive == '@function':
            add = rule.namespace.set_function

        # Register the mixin for every possible arity it takes
        if argspec_node.slurp or argspec_node.inject:
            add(funct, None, mixin)
        else:
            while len(new_params):
                add(funct, len(new_params), mixin)
                param = new_params.pop()
                if param not in defaults:
                    break
            if not new_params:
                add(funct, 0, mixin)

    @print_timing(10)
    def _do_include(self, rule, scope, block):
        """
        Implements @include, for @mixins
        """
        caller_namespace = rule.namespace
        caller_calculator = Calculator(caller_namespace)
        funct, caller_argspec = self._get_funct_def(rule, caller_calculator, block.argument)

        # Render the passed arguments, using the caller's namespace
        args, kwargs = caller_argspec.evaluate_call_args(caller_calculator)

        argc = len(args) + len(kwargs)
        try:
            mixin = caller_namespace.mixin(funct, argc)
        except KeyError:
            try:
                # TODO maybe? don't do this, once '...' works
                # Fallback to single parameter:
                mixin = caller_namespace.mixin(funct, 1)
            except KeyError:
                log.error("Mixin not found: %s:%d (%s)", funct, argc, rule.file_and_line, extra={'stack': True})
                return
            else:
                args = [List(args, use_comma=True)]
                # TODO what happens to kwargs?

        source_file = mixin[0]
        lineno = mixin[1]
        m_codestr = mixin[2]
        pristine_callee_namespace = mixin[3]
        callee_argspec = mixin[4]
        if caller_argspec.inject and callee_argspec.inject:
            # DEVIATION: Pass the ENTIRE local namespace to the mixin (yikes)
            callee_namespace = Namespace.derive_from(
                caller_namespace,
                pristine_callee_namespace)
        else:
            callee_namespace = pristine_callee_namespace.derive()

        self._populate_namespace_from_call(
            "Mixin {0}".format(funct),
            callee_namespace, mixin, args, kwargs)

        _rule = SassRule(
            source_file=source_file,
            lineno=lineno,
            unparsed_contents=m_codestr,
            namespace=callee_namespace,

            # rule
            import_key=rule.import_key,
            options=rule.options,
            properties=rule.properties,
            extends_selectors=rule.extends_selectors,
            ancestry=rule.ancestry,
            nested=rule.nested,
        )

        _rule.options['@content'] = block.unparsed_contents
        self.manage_children(_rule, scope)

    @print_timing(10)
    def _do_content(self, rule, scope, block):
        """
        Implements @content
        """
        if '@content' not in rule.options:
            log.error("Content string not found for @content (%s)", rule.file_and_line)
        rule.unparsed_contents = rule.options.pop('@content', '')
        self.manage_children(rule, scope)

    @print_timing(10)
    def _do_import(self, rule, scope, block):
        """
        Implements @import
        Load and import mixins and functions and rules
        """
        # Protect against going to prohibited places...
        if any(scary_token in block.argument for scary_token in ('..', '://', 'url(')):
            rule.properties.append((block.prop, None))
            return

        full_filename = None
        names = block.argument.split(',')
        for name in names:
            name = dequote(name.strip())

            source_file = None
            full_filename, seen_paths = self._find_import(rule, name)

            if full_filename is None:
                i_codestr = self._do_magic_import(rule, scope, block)

                if i_codestr is not None:
                    source_file = SourceFile.from_string(i_codestr)

            elif full_filename in self.source_file_index:
                source_file = self.source_file_index[full_filename]

            else:
                with open(full_filename) as f:
                    source = f.read()
                source_file = SourceFile(
                    full_filename,
                    source,
                    parent_dir=os.path.realpath(os.path.dirname(full_filename)),
                )

                self.source_files.append(source_file)
                self.source_file_index[full_filename] = source_file

            if source_file is None:
                load_paths_msg = "\nLoad paths:\n\t%s" % "\n\t".join(seen_paths)
                log.warn("File to import not found or unreadable: '%s' (%s)%s", name, rule.file_and_line, load_paths_msg)
                continue

            import_key = (name, source_file.parent_dir)
            if rule.namespace.has_import(import_key):
                # If already imported in this scope, skip
                continue

            _rule = SassRule(
                source_file=source_file,
                lineno=block.lineno,
                import_key=import_key,
                unparsed_contents=source_file.contents,

                # rule
                options=rule.options,
                properties=rule.properties,
                extends_selectors=rule.extends_selectors,
                ancestry=rule.ancestry,
                namespace=rule.namespace,
            )
            rule.namespace.add_import(import_key, rule.import_key, rule.file_and_line)
            self.manage_children(_rule, scope)

    def _find_import(self, rule, name):
        """Find the file referred to by an @import.

        Takes a name from an @import and returns an absolute path, or None.
        """
        name, ext = os.path.splitext(name)
        if ext:
            search_exts = [ext]
        else:
            search_exts = ['.scss', '.sass']

        dirname, name = os.path.split(name)

        seen_paths = []

        for path in self.search_paths:
            for basepath in [rule.source_file.parent_dir, '.']:
                full_path = os.path.realpath(os.path.join(basepath, path, dirname))

                if full_path in seen_paths:
                    continue
                seen_paths.append(full_path)

                for prefix, suffix in product(('_', ''), search_exts):
                    full_filename = os.path.join(full_path, prefix + name + suffix)
                    if os.path.exists(full_filename):
                        return full_filename, seen_paths

        return None, seen_paths

    @print_timing(10)
    def _do_magic_import(self, rule, scope, block):
        """
        Implements @import for sprite-maps
        Imports magic sprite map directories
        """
        if callable(config.STATIC_ROOT):
            files = sorted(config.STATIC_ROOT(block.argument))
        else:
            glob_path = os.path.join(config.STATIC_ROOT, block.argument)
            files = glob.glob(glob_path)
            files = sorted((file[len(config.STATIC_ROOT):], None) for file in files)

        if not files:
            return

        # Build magic context
        map_name = os.path.normpath(os.path.dirname(block.argument)).replace('\\', '_').replace('/', '_')
        kwargs = {}

        calculator = Calculator(rule.namespace)

        def setdefault(var, val):
            _var = '$' + map_name + '-' + var
            if _var in rule.context:
                kwargs[var] = calculator.interpolate(rule.context[_var], rule, self._library)
            else:
                rule.context[_var] = val
                kwargs[var] = calculator.interpolate(val, rule, self._library)
            return rule.context[_var]

        setdefault('sprite-base-class', String('.' + map_name + '-sprite', quotes=None))
        setdefault('sprite-dimensions', Boolean(False))
        position = setdefault('position', Number(0, '%'))
        spacing = setdefault('spacing', Number(0))
        repeat = setdefault('repeat', String('no-repeat', quotes=None))
        names = tuple(os.path.splitext(os.path.basename(file))[0] for file, storage in files)
        for n in names:
            setdefault(n + '-position', position)
            setdefault(n + '-spacing', spacing)
            setdefault(n + '-repeat', repeat)
        rule.context['$' + map_name + '-' + 'sprites'] = sprite_map(block.argument, **kwargs)
        ret = '''
            @import "compass/utilities/sprites/base";

            // All sprites should extend this class
            // The %(map_name)s-sprite mixin will do so for you.
            #{$%(map_name)s-sprite-base-class} {
                background: $%(map_name)s-sprites;
            }

            // Use this to set the dimensions of an element
            // based on the size of the original image.
            @mixin %(map_name)s-sprite-dimensions($name) {
                @include sprite-dimensions($%(map_name)s-sprites, $name);
            }

            // Move the background position to display the sprite.
            @mixin %(map_name)s-sprite-position($name, $offset-x: 0, $offset-y: 0) {
                @include sprite-position($%(map_name)s-sprites, $name, $offset-x, $offset-y);
            }

            // Extends the sprite base class and set the background position for the desired sprite.
            // It will also apply the image dimensions if $dimensions is true.
            @mixin %(map_name)s-sprite($name, $dimensions: $%(map_name)s-sprite-dimensions, $offset-x: 0, $offset-y: 0) {
                @extend #{$%(map_name)s-sprite-base-class};
                @include sprite($%(map_name)s-sprites, $name, $dimensions, $offset-x, $offset-y);
            }

            @mixin %(map_name)s-sprites($sprite-names, $dimensions: $%(map_name)s-sprite-dimensions) {
                @include sprites($%(map_name)s-sprites, $sprite-names, $%(map_name)s-sprite-base-class, $dimensions);
            }

            // Generates a class for each sprited image.
            @mixin all-%(map_name)s-sprites($dimensions: $%(map_name)s-sprite-dimensions) {
                @include %(map_name)s-sprites(%(sprites)s, $dimensions);
            }
        ''' % {'map_name': map_name, 'sprites': ' '.join(names)}
        return ret

    @print_timing(10)
    def _do_if(self, rule, scope, block):
        """
        Implements @if and @else if
        """
        # "@if" indicates whether any kind of `if` since the last `@else` has
        # succeeded, in which case `@else if` should be skipped
        if block.directive != '@if':
            if '@if' not in rule.options:
                raise SyntaxError("@else with no @if (%s)" % (rule.file_and_line,))
            if rule.options['@if']:
                # Last @if succeeded; stop here
                return

        calculator = Calculator(rule.namespace)
        condition = calculator.calculate(block.argument)
        if condition:
            inner_rule = rule.copy()
            inner_rule.unparsed_contents = block.unparsed_contents
            if not rule.options.get('control_scoping', config.CONTROL_SCOPING):  # TODO: maybe make this scoping mode for contol structures as the default as a default deviation
                # DEVIATION: Allow not creating a new namespace
                inner_rule.namespace = rule.namespace
            self.manage_children(inner_rule, scope)
        rule.options['@if'] = condition

    @print_timing(10)
    def _do_else(self, rule, scope, block):
        """
        Implements @else
        """
        if '@if' not in rule.options:
            log.error("@else with no @if (%s)", rule.file_and_line)
        val = rule.options.pop('@if', True)
        if not val:
            inner_rule = rule.copy()
            inner_rule.unparsed_contents = block.unparsed_contents
            inner_rule.namespace = rule.namespace  # DEVIATION: Commenting this line gives the Sass bahavior
            inner_rule.unparsed_contents = block.unparsed_contents
            self.manage_children(inner_rule, scope)

    @print_timing(10)
    def _do_for(self, rule, scope, block):
        """
        Implements @for
        """
        var, _, name = block.argument.partition(' from ')
        frm, _, through = name.partition(' through ')
        if not through:
            frm, _, through = frm.partition(' to ')
        calculator = Calculator(rule.namespace)
        frm = calculator.calculate(frm)
        through = calculator.calculate(through)
        try:
            frm = int(float(frm))
            through = int(float(through))
        except ValueError:
            return

        if frm > through:
            # DEVIATION: allow reversed '@for .. from .. through' (same as enumerate() and range())
            frm, through = through, frm
            rev = reversed
        else:
            rev = lambda x: x
        var = var.strip()
        var = calculator.do_glob_math(var)
        var = normalize_var(var)

        inner_rule = rule.copy()
        inner_rule.unparsed_contents = block.unparsed_contents
        if not rule.options.get('control_scoping', config.CONTROL_SCOPING):  # TODO: maybe make this scoping mode for contol structures as the default as a default deviation
            # DEVIATION: Allow not creating a new namespace
            inner_rule.namespace = rule.namespace

        for i in rev(range(frm, through + 1)):
            inner_rule.namespace.set_variable(var, Number(i))
            self.manage_children(inner_rule, scope)

    @print_timing(10)
    def _do_each(self, rule, scope, block):
        """
        Implements @each
        """
        varstring, _, valuestring = block.argument.partition(' in ')
        calculator = Calculator(rule.namespace)
        values = calculator.calculate(valuestring)
        if not values:
            return

        varlist = varstring.split(",")
        varlist = [
            normalize_var(calculator.do_glob_math(var.strip()))
            for var in varlist
        ]

        inner_rule = rule.copy()
        inner_rule.unparsed_contents = block.unparsed_contents
        if not rule.options.get('control_scoping', config.CONTROL_SCOPING):  # TODO: maybe make this scoping mode for contol structures as the default as a default deviation
            # DEVIATION: Allow not creating a new namespace
            inner_rule.namespace = rule.namespace

        for v in List.from_maybe(values):
            v = List.from_maybe(v)
            for i, var in enumerate(varlist):
                if i >= len(v):
                    value = Null()
                else:
                    value = v[i]
                inner_rule.namespace.set_variable(var, value)
            self.manage_children(inner_rule, scope)

    @print_timing(10)
    def _do_while(self, rule, scope, block):
        """
        Implements @while
        """
        calculator = Calculator(rule.namespace)
        first_condition = condition = calculator.calculate(block.argument)
        while condition:
            inner_rule = rule.copy()
            inner_rule.unparsed_contents = block.unparsed_contents
            if not rule.options.get('control_scoping', config.CONTROL_SCOPING):  # TODO: maybe make this scoping mode for contol structures as the default as a default deviation
                # DEVIATION: Allow not creating a new namespace
                inner_rule.namespace = rule.namespace
            self.manage_children(inner_rule, scope)
            condition = calculator.calculate(block.argument)
        rule.options['@if'] = first_condition

    @print_timing(10)
    def _get_variables(self, rule, scope, block):
        """
        Implements @variables and @vars
        """
        _rule = rule.copy()
        _rule.unparsed_contents = block.unparsed_contents
        _rule.namespace = rule.namespace
        _rule.properties = {}
        self.manage_children(_rule, scope)
        for name, value in _rule.properties.items():
            rule.namespace.set_variable(name, value)

    @print_timing(10)
    def _get_properties(self, rule, scope, block):
        """
        Implements properties and variables extraction and assignment
        """
        prop, raw_value = (_prop_split_re.split(block.prop, 1) + [None])[:2]
        try:
            is_var = (block.prop[len(prop)] == '=')
        except IndexError:
            is_var = False
        calculator = Calculator(rule.namespace)
        prop = prop.strip()
        prop = calculator.do_glob_math(prop)
        if not prop:
            return

        # Parse the value and determine whether it's a default assignment
        is_default = False
        if raw_value is not None:
            raw_value = raw_value.strip()
            if prop.startswith('$'):
                raw_value, subs = re.subn(r'(?i)\s+!default\Z', '', raw_value)
                if subs:
                    is_default = True

        _prop = (scope or '') + prop
        if is_var or prop.startswith('$') and raw_value is not None:
            # Variable assignment
            _prop = normalize_var(_prop)
            try:
                existing_value = rule.namespace.variable(_prop)
            except KeyError:
                existing_value = None

            is_defined = existing_value is not None and not existing_value.is_null
            if is_default and is_defined:
                pass
            else:
                if is_defined and prop.startswith('$') and prop[1].isupper():
                    log.warn("Constant %r redefined", prop)

                # Variable assignment is an expression, so it always performs
                # real division
                value = calculator.calculate(raw_value, divide=True)
                rule.namespace.set_variable(_prop, value)
        else:
            # Regular property destined for output
            _prop = calculator.apply_vars(_prop)
            if raw_value is None:
                value = None
            else:
                value = calculator.calculate(raw_value)

            if value is None:
                pass
            elif isinstance(value, six.string_types):
                # TODO kill this branch
                pass
            else:
                style = self.scss_opts.get('style', config.STYLE)
                compress = style in (True, 'compressed')
                value = value.render(compress=compress)

            rule.properties.append((_prop, value))

    @print_timing(10)
    def _nest_at_rules(self, rule, scope, block):
        """
        Implements @-blocks
        """
        # Interpolate the current block
        # TODO this seems like it should be done in the block header.  and more
        # generally?
        calculator = Calculator(rule.namespace)
        block.header.argument = calculator.apply_vars(block.header.argument)

        # TODO merge into RuleAncestry
        new_ancestry = list(rule.ancestry.headers)
        if block.directive == '@media' and new_ancestry:
            for i, header in reversed(list(enumerate(new_ancestry))):
                if header.is_selector:
                    continue
                elif header.directive == '@media':
                    from scss.rule import BlockAtRuleHeader
                    new_ancestry[i] = BlockAtRuleHeader(
                        '@media',
                        "%s and %s" % (header.argument, block.argument))
                    break
                else:
                    new_ancestry.insert(i, block.header)
            else:
                new_ancestry.insert(0, block.header)
        else:
            new_ancestry.append(block.header)

        from scss.rule import RuleAncestry
        rule.descendants += 1
        new_rule = SassRule(
            source_file=rule.source_file,
            import_key=rule.import_key,
            lineno=block.lineno,
            unparsed_contents=block.unparsed_contents,

            options=rule.options.copy(),
            #properties
            #extends_selectors
            ancestry=RuleAncestry(new_ancestry),

            namespace=rule.namespace.derive(),
            nested=rule.nested + 1,
        )
        self.rules.append(new_rule)
        rule.namespace.use_import(rule.import_key)
        self.manage_children(new_rule, scope)

        if new_rule.options.get('warn_unused'):
            for name, file_and_line in new_rule.namespace.unused_imports():
                log.warn("Unused @import: '%s' (%s)", name, file_and_line)

    @print_timing(10)
    def _nest_rules(self, rule, scope, block):
        """
        Implements Nested CSS rules
        """
        calculator = Calculator(rule.namespace)
        raw_selectors = calculator.do_glob_math(block.prop)
        # DEVIATION: ruby sass doesn't support bare variables in selectors
        raw_selectors = calculator.apply_vars(raw_selectors)
        c_selectors, c_parents = self.parse_selectors(raw_selectors)

        new_ancestry = rule.ancestry.with_nested_selectors(c_selectors)

        rule.descendants += 1
        new_rule = SassRule(
            source_file=rule.source_file,
            import_key=rule.import_key,
            lineno=block.lineno,
            unparsed_contents=block.unparsed_contents,

            options=rule.options.copy(),
            #properties
            extends_selectors=c_parents,
            ancestry=new_ancestry,

            namespace=rule.namespace.derive(),
            nested=rule.nested + 1,
        )
        self.rules.append(new_rule)
        rule.namespace.use_import(rule.import_key)
        self.manage_children(new_rule, scope)

        if new_rule.options.get('warn_unused'):
            for name, file_and_line in new_rule.namespace.unused_imports():
                log.warn("Unused @import: '%s' (%s)", name, file_and_line)

    @print_timing(3)
    def apply_extends(self):
        """Run through the given rules and translate all the pending @extends
        declarations into real selectors on parent rules.

        The list is modified in-place and also sorted in dependency order.
        """
        # Game plan: for each rule that has an @extend, add its selectors to
        # every rule that matches that @extend.
        # First, rig a way to find arbitrary selectors quickly.  Most selectors
        # revolve around elements, classes, and IDs, so parse those out and use
        # them as a rough key.  Ignore order and duplication for now.
        key_to_selectors = defaultdict(set)
        selector_to_rules = defaultdict(list)
        # DEVIATION: These are used to rearrange rules in dependency order, so
        # an @extended parent appears in the output before a child.  Sass does
        # not do this, and the results may be unexpected.  Pending removal.
        rule_order = dict()
        rule_dependencies = dict()
        order = 0
        for rule in self.rules:
            rule_order[rule] = order
            # Rules are ultimately sorted by the earliest rule they must
            # *precede*, so every rule should "depend" on the next one
            rule_dependencies[rule] = [order + 1]
            order += 1

            for selector in rule.selectors:
                for key in selector.lookup_key():
                    key_to_selectors[key].add(selector)
                selector_to_rules[selector].append(rule)

        # Now go through all the rules with an @extends and find their parent
        # rules.
        for rule in self.rules:
            for selector in rule.extends_selectors:
                # This is a little dirty.  intersection isn't a class method.
                # Don't think about it too much.
                candidates = set.intersection(*(
                    key_to_selectors[key] for key in selector.lookup_key()))
                extendable_selectors = [
                    candidate for candidate in candidates
                    if candidate.is_superset_of(selector)]

                if not extendable_selectors:
                    log.warn(
                        "Can't find any matching rules to extend: %s"
                        % selector.render())
                    continue

                # Armed with a set of selectors that this rule can extend, do
                # some substitution and modify the appropriate parent rules
                for extendable_selector in extendable_selectors:
                    # list() shields us from problems mutating the list within
                    # this loop, which can happen in the case of @extend loops
                    parent_rules = list(selector_to_rules[extendable_selector])
                    for parent_rule in parent_rules:
                        if parent_rule is rule:
                            # Don't extend oneself
                            continue

                        more_parent_selectors = []

                        for rule_selector in rule.selectors:
                            more_parent_selectors.extend(
                                extendable_selector.substitute(
                                    selector, rule_selector))

                        for parent in more_parent_selectors:
                            # Update indices, in case any later rules try to
                            # extend this one
                            for key in parent.lookup_key():
                                key_to_selectors[key].add(parent)
                            # TODO this could lead to duplicates?  maybe should
                            # be a set too
                            selector_to_rules[parent].append(parent_rule)

                        parent_rule.ancestry = (
                            parent_rule.ancestry.with_more_selectors(
                                more_parent_selectors))
                        rule_dependencies[parent_rule].append(rule_order[rule])

        self.rules.sort(key=lambda rule: min(rule_dependencies[rule]))

    @print_timing(3)
    def parse_properties(self):
        css_files = []
        seen_files = set()
        rules_by_file = {}

        for rule in self.rules:
            source_file = rule.source_file
            rules_by_file.setdefault(source_file, []).append(rule)

            if rule.is_empty:
                continue

            if source_file not in seen_files:
                seen_files.add(source_file)
                css_files.append(source_file)

        return rules_by_file, css_files

    @print_timing(3)
    def create_css(self, rules):
        """
        Generate the final CSS string
        """
        style = self.scss_opts.get('style', config.STYLE)
        debug_info = self.scss_opts.get('debug_info', False)

        if style == 'legacy' or style is False:
            sc, sp, tb, nst, srnl, nl, rnl, lnl, dbg = True, ' ', '  ', False, '', '\n', '\n', '\n', debug_info
        elif style == 'compressed' or style is True:
            sc, sp, tb, nst, srnl, nl, rnl, lnl, dbg = False, '', '', False, '', '', '', '', False
        elif style == 'compact':
            sc, sp, tb, nst, srnl, nl, rnl, lnl, dbg = True, ' ', '', False, '\n', ' ', '\n', ' ', debug_info
        elif style == 'expanded':
            sc, sp, tb, nst, srnl, nl, rnl, lnl, dbg = True, ' ', '  ', False, '\n', '\n', '\n', '\n', debug_info
        else:  # if style == 'nested':
            sc, sp, tb, nst, srnl, nl, rnl, lnl, dbg = True, ' ', '  ', True, '\n', '\n', '\n', ' ', debug_info

        return self._create_css(rules, sc, sp, tb, nst, srnl, nl, rnl, lnl, dbg)

    def _textwrap(self, txt, width=70):
        if not hasattr(self, '_textwrap_wordsep_re'):
            self._textwrap_wordsep_re = re.compile(r'(?<=,)\s+')
            self._textwrap_strings_re = re.compile(r'''(["'])(?:(?!\1)[^\\]|\\.)*\1''')

        # First, remove commas from anything within strings (marking commas as \0):
        def _repl(m):
            ori = m.group(0)
            fin = ori.replace(',', '\0')
            if ori != fin:
                subs[fin] = ori
            return fin
        subs = {}
        txt = self._textwrap_strings_re.sub(_repl, txt)

        # Mark split points for word separators using (marking spaces with \1):
        txt = self._textwrap_wordsep_re.sub('\1', txt)

        # Replace all the strings back:
        for fin, ori in subs.items():
            txt = txt.replace(fin, ori)

        # Split in chunks:
        chunks = txt.split('\1')

        # Break in lines of at most long_width width appending chunks:
        ln = ''
        lines = []
        long_width = int(width * 1.2)
        for chunk in chunks:
            _ln = ln + ' ' if ln else ''
            _ln += chunk
            if len(ln) >= width or len(_ln) >= long_width:
                if ln:
                    lines.append(ln)
                _ln = chunk
            ln = _ln
        if ln:
            lines.append(ln)

        return lines

    def _create_css(self, rules, sc=True, sp=' ', tb='  ', nst=True, srnl='\n', nl='\n', rnl='\n', lnl='', debug_info=False):
        skip_selectors = False

        prev_ancestry_headers = []

        total_rules = 0
        total_selectors = 0

        result = ''
        dangling_property = False
        separate = False
        nesting = current_nesting = last_nesting = -1 if nst else 0
        nesting_stack = []
        for rule in rules:
            nested = rule.nested
            if nested <= 1:
                separate = True

            if nst:
                last_nesting = current_nesting
                current_nesting = nested

                delta_nesting = current_nesting - last_nesting
                if delta_nesting > 0:
                    nesting_stack += [nesting] * delta_nesting
                elif delta_nesting < 0:
                    nesting_stack = nesting_stack[:delta_nesting]
                    nesting = nesting_stack[-1]

            if rule.is_empty:
                continue

            if nst:
                nesting += 1

            ancestry = rule.ancestry
            ancestry_len = len(ancestry)

            first_mismatch = 0
            for i, (old_header, new_header) in enumerate(zip(prev_ancestry_headers, ancestry.headers)):
                if old_header != new_header:
                    first_mismatch = i
                    break

            # When sc is False, sets of properties are printed without a
            # trailing semicolon.  If the previous block isn't being closed,
            # that trailing semicolon needs adding in to separate the last
            # property from the next rule.
            if not sc and dangling_property and first_mismatch >= len(prev_ancestry_headers):
                result += ';'

            # Close blocks and outdent as necessary
            for i in range(len(prev_ancestry_headers), first_mismatch, -1):
                result += tb * (i - 1) + '}' + rnl

            # Open new blocks as necessary
            for i in range(first_mismatch, ancestry_len):
                header = ancestry.headers[i]

                if separate:
                    if result:
                        result += srnl
                    separate = False
                if debug_info:
                    if not rule.source_file.is_string:
                        filename = rule.source_file.filename
                        lineno = str(rule.lineno)
                        if debug_info == 'comments':
                            result += tb * (i + nesting) + "/* file: %s, line: %s */" % (filename, lineno) + nl
                        else:
                            filename = _escape_chars_re.sub(r'\\\1', filename)
                            result += tb * (i + nesting) + "@media -sass-debug-info{filename{font-family:file\:\/\/%s}line{font-family:\\00003%s}}" % (filename, lineno) + nl

                if header.is_selector:
                    header_string = header.render(sep=',' + sp, super_selector=self.super_selector)
                    if nl:
                        header_string = (nl + tb * (i + nesting)).join(self._textwrap(header_string))
                else:
                    header_string = header.render()
                result += tb * (i + nesting) + header_string + sp + '{' + nl

                total_rules += 1
                if header.is_selector:
                    total_selectors += 1

            prev_ancestry_headers = ancestry.headers
            dangling_property = False

            if not skip_selectors:
                result += self._print_properties(rule.properties, sc, sp, tb * (ancestry_len + nesting), nl, lnl)
                dangling_property = True

        # Close all remaining blocks
        for i in reversed(range(len(prev_ancestry_headers))):
            result += tb * i + '}' + rnl

        return (result, total_rules, total_selectors)

    def _print_properties(self, properties, sc=True, sp=' ', tb='', nl='\n', lnl=' '):
        result = ''
        last_prop_index = len(properties) - 1
        for i, (name, value) in enumerate(properties):
            if value is None:
                prop = name
            elif value:
                if nl:
                    value = (nl + tb + tb).join(self._textwrap(value))
                prop = name + ':' + sp + value
            else:
                # Empty string means there's supposed to be a value but it
                # evaluated to nothing; skip this
                # TODO interacts poorly with last_prop_index
                continue

            if i == last_prop_index:
                if sc:
                    result += tb + prop + ';' + lnl
                else:
                    result += tb + prop + lnl
            else:
                result += tb + prop + ';' + nl
        return result


# TODO: this should inherit from SassError, but can't, because that assumes
# it's wrapping another error.  fix this with the exception hierarchy
class SassReturn(Exception):
    """Special control-flow exception used to hop up the stack from a Sass
    function's ``@return``.
    """
    def __init__(self, retval):
        self.retval = retval
        Exception.__init__(self)

    def __str__(self):
        return "Returning {0!r}".format(self.retval)

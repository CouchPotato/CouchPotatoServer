from __future__ import absolute_import
from __future__ import print_function

from functools import partial
import logging
import operator
import re

import six

import scss.config as config
from scss.cssdefs import COLOR_NAMES, is_builtin_css_function, _expr_glob_re, _interpolate_re
from scss.errors import SassError, SassEvaluationError, SassParseError
from scss.rule import Namespace
from scss.types import Boolean, Color, List, Map, Null, Number, String, Undefined, Value
from scss.util import dequote, normalize_var

################################################################################
# Load C acceleration modules
Scanner = None
try:
    from scss._speedups import Scanner
except ImportError:
    from scss._native import Scanner

log = logging.getLogger(__name__)


class Calculator(object):
    """Expression evaluator."""

    ast_cache = {}

    def __init__(self, namespace=None):
        if namespace is None:
            self.namespace = Namespace()
        else:
            self.namespace = namespace

    def _pound_substitute(self, result):
        expr = result.group(1)
        value = self.evaluate_expression(expr)

        if value is None:
            return self.apply_vars(expr)
        elif value.is_null:
            return ""
        else:
            return dequote(value.render())

    def do_glob_math(self, cont):
        """Performs #{}-interpolation.  The result is always treated as a fixed
        syntactic unit and will not be re-evaluated.
        """
        # TODO that's a lie!  this should be in the parser for most cases.
        cont = str(cont)
        if '#{' not in cont:
            return cont
        cont = _expr_glob_re.sub(self._pound_substitute, cont)
        return cont

    def apply_vars(self, cont):
        # TODO this is very complicated.  it should go away once everything
        # valid is actually parseable.
        if isinstance(cont, six.string_types) and '$' in cont:
            try:
                # Optimization: the full cont is a variable in the context,
                cont = self.namespace.variable(cont)
            except KeyError:
                # Interpolate variables:
                def _av(m):
                    v = None
                    n = m.group(2)
                    try:
                        v = self.namespace.variable(n)
                    except KeyError:
                        if config.FATAL_UNDEFINED:
                            raise SyntaxError("Undefined variable: '%s'." % n)
                        else:
                            if config.VERBOSITY > 1:
                                log.error("Undefined variable '%s'", n, extra={'stack': True})
                            return n
                    else:
                        if v:
                            if not isinstance(v, six.string_types):
                                v = v.render()
                            # TODO this used to test for _dequote
                            if m.group(1):
                                v = dequote(v)
                        else:
                            v = m.group(0)
                        return v

                cont = _interpolate_re.sub(_av, cont)
        # TODO this is surprising and shouldn't be here
        cont = self.do_glob_math(cont)
        return cont

    def calculate(self, _base_str, divide=False):
        better_expr_str = _base_str

        better_expr_str = self.do_glob_math(better_expr_str)

        better_expr_str = self.evaluate_expression(better_expr_str, divide=divide)

        if better_expr_str is None:
            better_expr_str = String.unquoted(self.apply_vars(_base_str))

        return better_expr_str

    # TODO only used by magic-import...?
    def interpolate(self, var):
        value = self.namespace.variable(var)
        if var != value and isinstance(value, six.string_types):
            _vi = self.evaluate_expression(value)
            if _vi is not None:
                value = _vi
        return value

    def evaluate_expression(self, expr, divide=False):
        try:
            ast = self.parse_expression(expr)
        except SassError:
            if config.DEBUG:
                raise
            else:
                return None

        try:
            return ast.evaluate(self, divide=divide)
        except Exception as e:
            raise SassEvaluationError(e, expression=expr)

    def parse_expression(self, expr, target='goal'):
        if not isinstance(expr, six.string_types):
            raise TypeError("Expected string, got %r" % (expr,))

        key = (target, expr)
        if key in self.ast_cache:
            return self.ast_cache[key]

        try:
            parser = SassExpression(SassExpressionScanner(expr))
            ast = getattr(parser, target)()
        except SyntaxError as e:
            raise SassParseError(e, expression=expr, expression_pos=parser._char_pos)

        self.ast_cache[key] = ast
        return ast


# ------------------------------------------------------------------------------
# Expression classes -- the AST resulting from a parse

class Expression(object):
    def __repr__(self):
        return '<%s()>' % (self.__class__.__name__)

    def evaluate(self, calculator, divide=False):
        """Evaluate this AST node, and return a Sass value.

        `divide` indicates whether a descendant node representing a division
        should be forcibly treated as a division.  See the commentary in
        `BinaryOp`.
        """
        raise NotImplementedError


class Parentheses(Expression):
    """An expression of the form `(foo)`.

    Only exists to force a slash to be interpreted as division when contained
    within parentheses.
    """
    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, repr(self.contents))

    def __init__(self, contents):
        self.contents = contents

    def evaluate(self, calculator, divide=False):
        return self.contents.evaluate(calculator, divide=True)


class UnaryOp(Expression):
    def __repr__(self):
        return '<%s(%s, %s)>' % (self.__class__.__name__, repr(self.op), repr(self.operand))

    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

    def evaluate(self, calculator, divide=False):
        return self.op(self.operand.evaluate(calculator, divide=True))


class BinaryOp(Expression):
    def __repr__(self):
        return '<%s(%s, %s, %s)>' % (self.__class__.__name__, repr(self.op), repr(self.left), repr(self.right))

    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def evaluate(self, calculator, divide=False):
        left = self.left.evaluate(calculator, divide=True)
        right = self.right.evaluate(calculator, divide=True)

        # Special handling of division: treat it as a literal slash if both
        # operands are literals, there are parentheses, or this is part of a
        # bigger expression.
        # The first condition is covered by the type check.  The other two are
        # covered by the `divide` argument: other nodes that perform arithmetic
        # will pass in True, indicating that this should always be a division.
        if (
            self.op is operator.truediv
            and not divide
            and isinstance(self.left, Literal)
            and isinstance(self.right, Literal)
        ):
            return String(left.render() + ' / ' + right.render(), quotes=None)

        return self.op(left, right)


class AnyOp(Expression):
    def __repr__(self):
        return '<%s(*%s)>' % (self.__class__.__name__, repr(self.op), repr(self.operands))

    def __init__(self, *operands):
        self.operands = operands

    def evaluate(self, calculator, divide=False):
        for operand in self.operands:
            value = operand.evaluate(calculator, divide=True)
            if value:
                return value
        return value


class AllOp(Expression):
    def __repr__(self):
        return '<%s(*%s)>' % (self.__class__.__name__, repr(self.operands))

    def __init__(self, *operands):
        self.operands = operands

    def evaluate(self, calculator, divide=False):
        for operand in self.operands:
            value = operand.evaluate(calculator, divide=True)
            if not value:
                return value
        return value


class NotOp(Expression):
    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, repr(self.operand))

    def __init__(self, operand):
        self.operand = operand

    def evaluate(self, calculator, divide=False):
        operand = self.operand.evaluate(calculator, divide=True)
        return Boolean(not(operand))


class CallOp(Expression):
    def __repr__(self):
        return '<%s(%s, %s)>' % (self.__class__.__name__, repr(self.func_name), repr(self.argspec))

    def __init__(self, func_name, argspec):
        self.func_name = func_name
        self.argspec = argspec

    def evaluate(self, calculator, divide=False):
        # TODO bake this into the context and options "dicts", plus library
        func_name = normalize_var(self.func_name)

        argspec_node = self.argspec

        # Turn the pairs of arg tuples into *args and **kwargs
        # TODO unclear whether this is correct -- how does arg, kwarg, arg
        # work?
        args, kwargs = argspec_node.evaluate_call_args(calculator)
        argspec_len = len(args) + len(kwargs)

        # Translate variable names to Python identifiers
        # TODO what about duplicate kw names?  should this happen in argspec?
        # how does that affect mixins?
        kwargs = dict(
            (key.lstrip('$').replace('-', '_'), value)
            for key, value in kwargs.items())

        # TODO merge this with the library
        funct = None
        try:
            funct = calculator.namespace.function(func_name, argspec_len)
            # @functions take a ns as first arg.  TODO: Python functions possibly
            # should too
            if getattr(funct, '__name__', None) == '__call':
                funct = partial(funct, calculator.namespace)
        except KeyError:
            try:
                # DEVIATION: Fall back to single parameter
                funct = calculator.namespace.function(func_name, 1)
                args = [List(args, use_comma=True)]
            except KeyError:
                if not is_builtin_css_function(func_name):
                    log.error("Function not found: %s:%s", func_name, argspec_len, extra={'stack': True})

        if funct:
            ret = funct(*args, **kwargs)
            if not isinstance(ret, Value):
                raise TypeError("Expected Sass type as return value, got %r" % (ret,))
            return ret

        # No matching function found, so render the computed values as a CSS
        # function call.  Slurpy arguments are expanded and named arguments are
        # unsupported.
        if kwargs:
            raise TypeError("The CSS function %s doesn't support keyword arguments." % (func_name,))

        # TODO another candidate for a "function call" sass type
        rendered_args = [arg.render() for arg in args]

        return String(
            u"%s(%s)" % (func_name, u", ".join(rendered_args)),
            quotes=None)


class Literal(Expression):
    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, repr(self.value))

    def __init__(self, value):
        if isinstance(value, Undefined) and config.FATAL_UNDEFINED:
            raise SyntaxError("Undefined literal.")
        else:
            self.value = value

    def evaluate(self, calculator, divide=False):
        return self.value


class Variable(Expression):
    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, repr(self.name))

    def __init__(self, name):
        self.name = name

    def evaluate(self, calculator, divide=False):
        try:
            value = calculator.namespace.variable(self.name)
        except KeyError:
            if config.FATAL_UNDEFINED:
                raise SyntaxError("Undefined variable: '%s'." % self.name)
            else:
                if config.VERBOSITY > 1:
                    log.error("Undefined variable '%s'", self.name, extra={'stack': True})
                return Undefined()
        else:
            if isinstance(value, six.string_types):
                evald = calculator.evaluate_expression(value)
                if evald is not None:
                    return evald
            return value


class ListLiteral(Expression):
    def __repr__(self):
        return '<%s(%s, comma=%s)>' % (self.__class__.__name__, repr(self.items), repr(self.comma))

    def __init__(self, items, comma=True):
        self.items = items
        self.comma = comma

    def evaluate(self, calculator, divide=False):
        items = [item.evaluate(calculator, divide=divide) for item in self.items]

        # Whether this is a "plain" literal matters for null removal: nulls are
        # left alone if this is a completely vanilla CSS property
        is_literal = True
        if divide:
            # TODO sort of overloading "divide" here...  rename i think
            is_literal = False
        elif not all(isinstance(item, Literal) for item in self.items):
            is_literal = False

        return List(items, use_comma=self.comma, is_literal=is_literal)


class MapLiteral(Expression):
    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, repr(self.pairs))

    def __init__(self, pairs):
        self.pairs = tuple((var, value) for var, value in pairs if value is not None)

    def evaluate(self, calculator, divide=False):
        scss_pairs = []
        for key, value in self.pairs:
            scss_pairs.append((
                key.evaluate(calculator),
                value.evaluate(calculator),
            ))

        return Map(scss_pairs)


class ArgspecLiteral(Expression):
    """Contains pairs of argument names and values, as parsed from a function
    definition or function call.

    Note that the semantics are somewhat ambiguous.  Consider parsing:

        $foo, $bar: 3

    If this appeared in a function call, $foo would refer to a value; if it
    appeared in a function definition, $foo would refer to an existing
    variable.  This it's up to the caller to use the right iteration function.
    """
    def __repr__(self):
        return '<%s(%s)>' % (self.__class__.__name__, repr(self.argpairs))

    def __init__(self, argpairs, slurp=None):
        # argpairs is a list of 2-tuples, parsed as though this were a function
        # call, so (variable name as string or None, default value as AST
        # node).
        # slurp is the name of a variable to receive slurpy arguments.
        self.argpairs = tuple(argpairs)
        if slurp is all:
            # DEVIATION: special syntax to allow injecting arbitrary arguments
            # from the caller to the callee
            self.inject = True
            self.slurp = None
        elif slurp:
            self.inject = False
            self.slurp = Variable(slurp)
        else:
            self.inject = False
            self.slurp = None

    def iter_list_argspec(self):
        yield None, ListLiteral(zip(*self.argpairs)[1])

    def iter_def_argspec(self):
        """Interpreting this literal as a function definition, yields pairs of
        (variable name as a string, default value as an AST node or None).
        """
        started_kwargs = False
        seen_vars = set()

        for var, value in self.argpairs:
            if var is None:
                # value is actually the name
                var = value
                value = None

                if started_kwargs:
                    raise SyntaxError(
                        "Required argument %r must precede optional arguments"
                        % (var.name,))

            else:
                started_kwargs = True

            if not isinstance(var, Variable):
                raise SyntaxError("Expected variable name, got %r" % (var,))

            if var.name in seen_vars:
                raise SyntaxError("Duplicate argument %r" % (var.name,))
            seen_vars.add(var.name)

            yield var.name, value

    def evaluate_call_args(self, calculator):
        """Interpreting this literal as a function call, return a 2-tuple of
        ``(args, kwargs)``.
        """
        args = []
        kwargs = {}
        for var_node, value_node in self.argpairs:
            value = value_node.evaluate(calculator, divide=True)
            if var_node is None:
                # Positional
                args.append(value)
            else:
                # Named
                if not isinstance(var_node, Variable):
                    raise SyntaxError("Expected variable name, got %r" % (var_node,))
                kwargs[var_node.name] = value

        # Slurpy arguments go on the end of the args
        if self.slurp:
            args.extend(self.slurp.evaluate(calculator, divide=True))

        return args, kwargs


def parse_bareword(word):
    if word in COLOR_NAMES:
        return Color.from_name(word)
    elif word == 'null':
        return Null()
    elif word == 'undefined':
        return Undefined()
    elif word == 'true':
        return Boolean(True)
    elif word == 'false':
        return Boolean(False)
    else:
        return String(word, quotes=None)


class Parser(object):
    def __init__(self, scanner):
        self._scanner = scanner
        self._pos = 0
        self._char_pos = 0

    def reset(self, input):
        self._scanner.reset(input)
        self._pos = 0
        self._char_pos = 0

    def _peek(self, types):
        """
        Returns the token type for lookahead; if there are any args
        then the list of args is the set of token types to allow
        """
        try:
            tok = self._scanner.token(self._pos, types)
            return tok[2]
        except SyntaxError:
            return None

    def _scan(self, type):
        """
        Returns the matched text, and moves to the next token
        """
        tok = self._scanner.token(self._pos, set([type]))
        self._char_pos = tok[0]
        if tok[2] != type:
            raise SyntaxError("SyntaxError[@ char %s: %s]" % (repr(tok[0]), "Trying to find " + type))
        self._pos += 1
        return tok[3]


################################################################################
## Grammar compiled using Yapps:

class SassExpressionScanner(Scanner):
    patterns = None
    _patterns = [
        ('":"', ':'),
        ('","', ','),
        ('[ \r\t\n]+', '[ \r\t\n]+'),
        ('LPAR', '\\(|\\['),
        ('RPAR', '\\)|\\]'),
        ('END', '$'),
        ('MUL', '[*]'),
        ('DIV', '/'),
        ('ADD', '[+]'),
        ('SUB', '-\\s'),
        ('SIGN', '-(?![a-zA-Z_])'),
        ('AND', '(?<![-\\w])and(?![-\\w])'),
        ('OR', '(?<![-\\w])or(?![-\\w])'),
        ('NOT', '(?<![-\\w])not(?![-\\w])'),
        ('NE', '!='),
        ('INV', '!'),
        ('EQ', '=='),
        ('LE', '<='),
        ('GE', '>='),
        ('LT', '<'),
        ('GT', '>'),
        ('DOTDOTDOT', '[.]{3}'),
        ('KWSTR', "'[^']*'(?=\\s*:)"),
        ('STR', "'[^']*'"),
        ('KWQSTR', '"[^"]*"(?=\\s*:)'),
        ('QSTR', '"[^"]*"'),
        ('UNITS', '(?<!\\s)(?:[a-zA-Z]+|%)(?![-\\w])'),
        ('KWNUM', '(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?=\\s*:)'),
        ('NUM', '(?:\\d+(?:\\.\\d*)?|\\.\\d+)'),
        ('KWCOLOR', '#(?:[a-fA-F0-9]{6}|[a-fA-F0-9]{3})(?![a-fA-F0-9])(?=\\s*:)'),
        ('COLOR', '#(?:[a-fA-F0-9]{6}|[a-fA-F0-9]{3})(?![a-fA-F0-9])'),
        ('KWVAR', '\\$[-a-zA-Z0-9_]+(?=\\s*:)'),
        ('SLURPYVAR', '\\$[-a-zA-Z0-9_]+(?=[.][.][.])'),
        ('VAR', '\\$[-a-zA-Z0-9_]+'),
        ('FNCT', '[-a-zA-Z_][-a-zA-Z0-9_]*(?=\\()'),
        ('KWID', '[-a-zA-Z_][-a-zA-Z0-9_]*(?=\\s*:)'),
        ('ID', '[-a-zA-Z_][-a-zA-Z0-9_]*'),
        ('BANG_IMPORTANT', '!important'),
    ]

    def __init__(self, input=None):
        if hasattr(self, 'setup_patterns'):
            self.setup_patterns(self._patterns)
        elif self.patterns is None:
            self.__class__.patterns = []
            for t, p in self._patterns:
                self.patterns.append((t, re.compile(p)))
        super(SassExpressionScanner, self).__init__(None, ['[ \r\t\n]+'], input)


class SassExpression(Parser):
    def goal(self):
        expr_lst = self.expr_lst()
        END = self._scan('END')
        return expr_lst

    def goal_argspec(self):
        argspec = self.argspec()
        END = self._scan('END')
        return argspec

    def argspec(self):
        _token_ = self._peek(self.argspec_rsts)
        if _token_ not in self.argspec_chks:
            if self._peek(self.argspec_rsts_) not in self.argspec_chks_:
                argspec_items = self.argspec_items()
                args, slurpy = argspec_items
                return ArgspecLiteral(args, slurp=slurpy)
            return ArgspecLiteral([])
        elif _token_ == 'SLURPYVAR':
            SLURPYVAR = self._scan('SLURPYVAR')
            DOTDOTDOT = self._scan('DOTDOTDOT')
            return ArgspecLiteral([], slurp=SLURPYVAR)
        else:  # == 'DOTDOTDOT'
            DOTDOTDOT = self._scan('DOTDOTDOT')
            return ArgspecLiteral([], slurp=all)

    def argspec_items(self):
        slurpy = None
        argspec_item = self.argspec_item()
        args = [argspec_item]
        if self._peek(self.argspec_items_rsts) == '","':
            self._scan('","')
            if self._peek(self.argspec_items_rsts_) not in self.argspec_chks_:
                _token_ = self._peek(self.argspec_items_rsts__)
                if _token_ == 'SLURPYVAR':
                    SLURPYVAR = self._scan('SLURPYVAR')
                    DOTDOTDOT = self._scan('DOTDOTDOT')
                    slurpy = SLURPYVAR
                elif _token_ == 'DOTDOTDOT':
                    DOTDOTDOT = self._scan('DOTDOTDOT')
                    slurpy = all
                else:  # in self.argspec_items_chks
                    argspec_items = self.argspec_items()
                    more_args, slurpy = argspec_items
                    args.extend(more_args)
        return args, slurpy

    def argspec_item(self):
        _token_ = self._peek(self.argspec_items_chks)
        if _token_ == 'KWVAR':
            KWVAR = self._scan('KWVAR')
            self._scan('":"')
            expr_slst = self.expr_slst()
            return (Variable(KWVAR), expr_slst)
        else:  # in self.argspec_item_chks
            expr_slst = self.expr_slst()
            return (None, expr_slst)

    def expr_map(self):
        map_item = self.map_item()
        pairs = [map_item]
        while self._peek(self.expr_map_rsts) == '","':
            self._scan('","')
            map_item = (None, None)
            if self._peek(self.expr_map_rsts_) not in self.expr_map_rsts:
                map_item = self.map_item()
            pairs.append(map_item)
        return MapLiteral(pairs)

    def map_item(self):
        kwatom = self.kwatom()
        self._scan('":"')
        expr_slst = self.expr_slst()
        return (kwatom, expr_slst)

    def expr_lst(self):
        expr_slst = self.expr_slst()
        v = [expr_slst]
        while self._peek(self.argspec_items_rsts) == '","':
            self._scan('","')
            expr_slst = self.expr_slst()
            v.append(expr_slst)
        return ListLiteral(v) if len(v) > 1 else v[0]

    def expr_slst(self):
        or_expr = self.or_expr()
        v = [or_expr]
        while self._peek(self.expr_slst_rsts) not in self.argspec_items_rsts:
            or_expr = self.or_expr()
            v.append(or_expr)
        return ListLiteral(v, comma=False) if len(v) > 1 else v[0]

    def or_expr(self):
        and_expr = self.and_expr()
        v = and_expr
        while self._peek(self.or_expr_rsts) == 'OR':
            OR = self._scan('OR')
            and_expr = self.and_expr()
            v = AnyOp(v, and_expr)
        return v

    def and_expr(self):
        not_expr = self.not_expr()
        v = not_expr
        while self._peek(self.and_expr_rsts) == 'AND':
            AND = self._scan('AND')
            not_expr = self.not_expr()
            v = AllOp(v, not_expr)
        return v

    def not_expr(self):
        _token_ = self._peek(self.argspec_item_chks)
        if _token_ != 'NOT':
            comparison = self.comparison()
            return comparison
        else:  # == 'NOT'
            NOT = self._scan('NOT')
            not_expr = self.not_expr()
            return NotOp(not_expr)

    def comparison(self):
        a_expr = self.a_expr()
        v = a_expr
        while self._peek(self.comparison_rsts) in self.comparison_chks:
            _token_ = self._peek(self.comparison_chks)
            if _token_ == 'LT':
                LT = self._scan('LT')
                a_expr = self.a_expr()
                v = BinaryOp(operator.lt, v, a_expr)
            elif _token_ == 'GT':
                GT = self._scan('GT')
                a_expr = self.a_expr()
                v = BinaryOp(operator.gt, v, a_expr)
            elif _token_ == 'LE':
                LE = self._scan('LE')
                a_expr = self.a_expr()
                v = BinaryOp(operator.le, v, a_expr)
            elif _token_ == 'GE':
                GE = self._scan('GE')
                a_expr = self.a_expr()
                v = BinaryOp(operator.ge, v, a_expr)
            elif _token_ == 'EQ':
                EQ = self._scan('EQ')
                a_expr = self.a_expr()
                v = BinaryOp(operator.eq, v, a_expr)
            else:  # == 'NE'
                NE = self._scan('NE')
                a_expr = self.a_expr()
                v = BinaryOp(operator.ne, v, a_expr)
        return v

    def a_expr(self):
        m_expr = self.m_expr()
        v = m_expr
        while self._peek(self.a_expr_rsts) in self.a_expr_chks:
            _token_ = self._peek(self.a_expr_chks)
            if _token_ == 'ADD':
                ADD = self._scan('ADD')
                m_expr = self.m_expr()
                v = BinaryOp(operator.add, v, m_expr)
            else:  # == 'SUB'
                SUB = self._scan('SUB')
                m_expr = self.m_expr()
                v = BinaryOp(operator.sub, v, m_expr)
        return v

    def m_expr(self):
        u_expr = self.u_expr()
        v = u_expr
        while self._peek(self.m_expr_rsts) in self.m_expr_chks:
            _token_ = self._peek(self.m_expr_chks)
            if _token_ == 'MUL':
                MUL = self._scan('MUL')
                u_expr = self.u_expr()
                v = BinaryOp(operator.mul, v, u_expr)
            else:  # == 'DIV'
                DIV = self._scan('DIV')
                u_expr = self.u_expr()
                v = BinaryOp(operator.truediv, v, u_expr)
        return v

    def u_expr(self):
        _token_ = self._peek(self.u_expr_rsts)
        if _token_ == 'SIGN':
            SIGN = self._scan('SIGN')
            u_expr = self.u_expr()
            return UnaryOp(operator.neg, u_expr)
        elif _token_ == 'ADD':
            ADD = self._scan('ADD')
            u_expr = self.u_expr()
            return UnaryOp(operator.pos, u_expr)
        else:  # in self.u_expr_chks
            atom = self.atom()
            return atom

    def atom(self):
        _token_ = self._peek(self.u_expr_chks)
        if _token_ == 'LPAR':
            LPAR = self._scan('LPAR')
            _token_ = self._peek(self.atom_rsts)
            if _token_ not in self.argspec_item_chks:
                expr_map = self.expr_map()
                v = expr_map
            else:  # in self.argspec_item_chks
                expr_lst = self.expr_lst()
                v = expr_lst
            RPAR = self._scan('RPAR')
            return Parentheses(v)
        elif _token_ == 'FNCT':
            FNCT = self._scan('FNCT')
            LPAR = self._scan('LPAR')
            argspec = self.argspec()
            RPAR = self._scan('RPAR')
            return CallOp(FNCT, argspec)
        elif _token_ == 'BANG_IMPORTANT':
            BANG_IMPORTANT = self._scan('BANG_IMPORTANT')
            return Literal(String(BANG_IMPORTANT, quotes=None))
        elif _token_ == 'ID':
            ID = self._scan('ID')
            return Literal(parse_bareword(ID))
        elif _token_ == 'NUM':
            NUM = self._scan('NUM')
            UNITS = None
            if self._peek(self.atom_rsts_) == 'UNITS':
                UNITS = self._scan('UNITS')
            return Literal(Number(float(NUM), unit=UNITS))
        elif _token_ == 'STR':
            STR = self._scan('STR')
            return Literal(String(STR[1:-1], quotes="'"))
        elif _token_ == 'QSTR':
            QSTR = self._scan('QSTR')
            return Literal(String(QSTR[1:-1], quotes='"'))
        elif _token_ == 'COLOR':
            COLOR = self._scan('COLOR')
            return Literal(Color.from_hex(COLOR, literal=True))
        else:  # == 'VAR'
            VAR = self._scan('VAR')
            return Variable(VAR)

    def kwatom(self):
        _token_ = self._peek(self.kwatom_rsts)
        if _token_ == '":"':
            pass
        elif _token_ == 'KWID':
            KWID = self._scan('KWID')
            return Literal(parse_bareword(KWID))
        elif _token_ == 'KWNUM':
            KWNUM = self._scan('KWNUM')
            UNITS = None
            if self._peek(self.kwatom_rsts_) == 'UNITS':
                UNITS = self._scan('UNITS')
            return Literal(Number(float(KWNUM), unit=UNITS))
        elif _token_ == 'KWSTR':
            KWSTR = self._scan('KWSTR')
            return Literal(String(KWSTR[1:-1], quotes="'"))
        elif _token_ == 'KWQSTR':
            KWQSTR = self._scan('KWQSTR')
            return Literal(String(KWQSTR[1:-1], quotes='"'))
        elif _token_ == 'KWCOLOR':
            KWCOLOR = self._scan('KWCOLOR')
            return Literal(Color.from_hex(COLOR, literal=True))
        else:  # == 'KWVAR'
            KWVAR = self._scan('KWVAR')
            return Variable(KWVAR)

    u_expr_chks = set(['LPAR', 'COLOR', 'QSTR', 'NUM', 'FNCT', 'STR', 'VAR', 'BANG_IMPORTANT', 'ID'])
    m_expr_rsts = set(['LPAR', 'SUB', 'QSTR', 'RPAR', 'MUL', 'DIV', 'BANG_IMPORTANT', 'LE', 'COLOR', 'NE', 'LT', 'NUM', 'GT', 'END', 'SIGN', 'GE', 'FNCT', 'STR', 'VAR', 'EQ', 'ID', 'AND', 'ADD', 'NOT', 'OR', '","'])
    argspec_items_rsts = set(['RPAR', 'END', '","'])
    expr_map_rsts = set(['RPAR', '","'])
    argspec_items_rsts__ = set(['KWVAR', 'LPAR', 'QSTR', 'SLURPYVAR', 'COLOR', 'DOTDOTDOT', 'SIGN', 'VAR', 'ADD', 'NUM', 'FNCT', 'STR', 'NOT', 'BANG_IMPORTANT', 'ID'])
    kwatom_rsts = set(['KWVAR', 'KWID', 'KWSTR', 'KWQSTR', 'KWCOLOR', '":"', 'KWNUM'])
    argspec_item_chks = set(['LPAR', 'COLOR', 'QSTR', 'SIGN', 'VAR', 'ADD', 'NUM', 'FNCT', 'STR', 'NOT', 'BANG_IMPORTANT', 'ID'])
    a_expr_chks = set(['ADD', 'SUB'])
    expr_slst_rsts = set(['LPAR', 'END', 'COLOR', 'QSTR', 'SIGN', 'VAR', 'ADD', 'NUM', 'RPAR', 'FNCT', 'STR', 'NOT', 'BANG_IMPORTANT', 'ID', '","'])
    or_expr_rsts = set(['LPAR', 'END', 'COLOR', 'QSTR', 'SIGN', 'VAR', 'ADD', 'NUM', 'RPAR', 'FNCT', 'STR', 'NOT', 'ID', 'BANG_IMPORTANT', 'OR', '","'])
    and_expr_rsts = set(['AND', 'LPAR', 'END', 'COLOR', 'QSTR', 'SIGN', 'VAR', 'ADD', 'NUM', 'RPAR', 'FNCT', 'STR', 'NOT', 'ID', 'BANG_IMPORTANT', 'OR', '","'])
    comparison_rsts = set(['LPAR', 'QSTR', 'RPAR', 'BANG_IMPORTANT', 'LE', 'COLOR', 'NE', 'LT', 'NUM', 'GT', 'END', 'SIGN', 'ADD', 'FNCT', 'STR', 'VAR', 'EQ', 'ID', 'AND', 'GE', 'NOT', 'OR', '","'])
    argspec_chks = set(['DOTDOTDOT', 'SLURPYVAR'])
    atom_rsts_ = set(['LPAR', 'SUB', 'QSTR', 'RPAR', 'VAR', 'MUL', 'DIV', 'BANG_IMPORTANT', 'LE', 'COLOR', 'NE', 'LT', 'NUM', 'GT', 'END', 'SIGN', 'GE', 'FNCT', 'STR', 'UNITS', 'EQ', 'ID', 'AND', 'ADD', 'NOT', 'OR', '","'])
    expr_map_rsts_ = set(['KWVAR', 'KWID', 'KWSTR', 'KWQSTR', 'RPAR', 'KWCOLOR', '":"', 'KWNUM', '","'])
    u_expr_rsts = set(['LPAR', 'COLOR', 'QSTR', 'SIGN', 'ADD', 'NUM', 'FNCT', 'STR', 'VAR', 'BANG_IMPORTANT', 'ID'])
    comparison_chks = set(['GT', 'GE', 'NE', 'LT', 'LE', 'EQ'])
    argspec_items_rsts_ = set(['KWVAR', 'LPAR', 'QSTR', 'END', 'SLURPYVAR', 'COLOR', 'DOTDOTDOT', 'SIGN', 'VAR', 'ADD', 'NUM', 'RPAR', 'FNCT', 'STR', 'NOT', 'BANG_IMPORTANT', 'ID'])
    a_expr_rsts = set(['LPAR', 'SUB', 'QSTR', 'RPAR', 'BANG_IMPORTANT', 'LE', 'COLOR', 'NE', 'LT', 'NUM', 'GT', 'END', 'SIGN', 'GE', 'FNCT', 'STR', 'VAR', 'EQ', 'ID', 'AND', 'ADD', 'NOT', 'OR', '","'])
    m_expr_chks = set(['MUL', 'DIV'])
    kwatom_rsts_ = set(['UNITS', '":"'])
    argspec_items_chks = set(['KWVAR', 'LPAR', 'COLOR', 'QSTR', 'SIGN', 'VAR', 'ADD', 'NUM', 'FNCT', 'STR', 'NOT', 'BANG_IMPORTANT', 'ID'])
    argspec_rsts = set(['KWVAR', 'LPAR', 'BANG_IMPORTANT', 'END', 'SLURPYVAR', 'COLOR', 'DOTDOTDOT', 'RPAR', 'VAR', 'ADD', 'NUM', 'FNCT', 'STR', 'NOT', 'QSTR', 'SIGN', 'ID'])
    atom_rsts = set(['KWVAR', 'KWID', 'KWSTR', 'BANG_IMPORTANT', 'LPAR', 'COLOR', 'KWQSTR', 'SIGN', 'KWCOLOR', 'VAR', 'ADD', 'NUM', '":"', 'STR', 'NOT', 'QSTR', 'KWNUM', 'ID', 'FNCT'])
    argspec_chks_ = set(['END', 'RPAR'])
    argspec_rsts_ = set(['KWVAR', 'LPAR', 'BANG_IMPORTANT', 'END', 'COLOR', 'QSTR', 'SIGN', 'VAR', 'ADD', 'NUM', 'FNCT', 'STR', 'NOT', 'RPAR', 'ID'])


### Grammar ends.
################################################################################

__all__ = ('Calculator',)

#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import print_function

from contextlib import contextmanager
import logging
import os
import re
import sys
from collections import deque

from scss import config
from scss.util import profiling
from scss import Scss, SourceFile, log
from scss import _prop_split_re
from scss.rule import SassRule
from scss.rule import UnparsedBlock
from scss.expression import Calculator
from scss.scss_meta import BUILD_INFO
from scss.errors import SassEvaluationError

try:
    raw_input
except NameError:
    raw_input = input

log.setLevel(logging.INFO)


def main():
    logging.basicConfig(format="%(levelname)s: %(message)s")

    from optparse import OptionGroup, OptionParser, SUPPRESS_HELP

    parser = OptionParser(usage="Usage: %prog [options] [file]",
                          description="Converts Scss files to CSS.",
                          add_help_option=False)
    parser.add_option("-i", "--interactive", action="store_true",
                      help="Run an interactive Scss shell")
    parser.add_option("-w", "--watch", metavar="DIR",
                      help="Watch the files in DIR, and recompile when they change")
    parser.add_option("-r", "--recursive", action="store_true", default=False,
                      help="Also watch directories inside of the watch directory")
    parser.add_option("-o", "--output", metavar="PATH",
                      help="Write output to PATH (a directory if using watch, a file otherwise)")
    parser.add_option("-s", "--suffix", metavar="STRING",
                      help="If using watch, a suffix added to the output filename (i.e. filename.STRING.css)")
    parser.add_option("--time", action="store_true",
                      help="Display compliation times")
    parser.add_option("--debug-info", action="store_true",
                      help="Turns on scss's debugging information")
    parser.add_option("--no-debug-info", action="store_false",
                      dest="debug_info", default=False,
                      help="Turns off scss's debugging information")
    parser.add_option("-T", "--test", action="store_true", help=SUPPRESS_HELP)
    parser.add_option("-t", "--style", metavar="NAME",
                      dest="style", default='nested',
                      help="Output style. Can be nested (default), compact, compressed, or expanded.")
    parser.add_option("-C", "--no-compress", action="store_false", dest="style", default=True,
                      help="Don't minify outputted CSS")
    parser.add_option("-?", action="help", help=SUPPRESS_HELP)
    parser.add_option("-h", "--help", action="help",
                      help="Show this message and exit")
    parser.add_option("-v", "--version", action="store_true",
                      help="Print version and exit")

    paths_group = OptionGroup(parser, "Resource Paths")
    paths_group.add_option("-I", "--load-path", metavar="PATH",
                      action="append", dest="load_paths",
                      help="Add a scss import path, may be given multiple times")
    paths_group.add_option("-S", "--static-root", metavar="PATH", dest="static_root",
                      help="Static root path (Where images and static resources are located)")
    paths_group.add_option("-A", "--assets-root", metavar="PATH", dest="assets_root",
                      help="Assets root path (Sprite images will be created here)")
    paths_group.add_option("-a", "--assets-url", metavar="URL", dest="assets_url",
                      help="URL to reach the files in your assets_root")
    paths_group.add_option("-F", "--fonts-root", metavar="PATH", dest="fonts_root",
                      help="Fonts root path (Where fonts are located)")
    paths_group.add_option("-f", "--fonts-url", metavar="PATH", dest="fonts_url",
                      help="URL to reach the fonts in your fonts_root")
    paths_group.add_option("--images-root", metavar="PATH", dest="images_root",
                      help="Images root path (Where images are located)")
    paths_group.add_option("--images-url", metavar="PATH", dest="images_url",
                      help="URL to reach the images in your images_root")
    paths_group.add_option("--cache-root", metavar="PATH", dest="cache_root",
                      help="Cache root path (Cache files will be created here)")
    parser.add_option_group(paths_group)

    parser.add_option("--sass", action="store_true",
                      dest="is_sass", default=None,
                      help="Sass mode")

    (options, args) = parser.parse_args()

    # General runtime configuration
    config.VERBOSITY = 0
    if options.time:
        config.VERBOSITY = 2
        
    if options.static_root is not None:
        config.STATIC_ROOT = options.static_root
    if options.assets_root is not None:
        config.ASSETS_ROOT = options.assets_root
        
    if options.fonts_root is not None:
        config.FONTS_ROOT = options.fonts_root
    if options.fonts_url is not None:
        config.FONTS_URL = options.fonts_url
        
    if options.images_root is not None:
        config.IMAGES_ROOT = options.images_root
    if options.images_url is not None:
        config.IMAGES_URL = options.images_url
        
    if options.cache_root is not None:
        config.CACHE_ROOT = options.cache_root
    if options.load_paths is not None:
        # TODO: Convert global LOAD_PATHS to a list. Use it directly.
        # Doing the above will break backwards compatibility!
        if hasattr(config.LOAD_PATHS, 'split'):
            load_path_list = [p.strip() for p in config.LOAD_PATHS.split(',')]
        else:
            load_path_list = list(config.LOAD_PATHS)

        for path_param in options.load_paths:
            for p in path_param.replace(os.pathsep, ',').replace(';', ',').split(','):
                p = p.strip()
                if p and p not in load_path_list:
                    load_path_list.append(p)

        # TODO: Remove this once global LOAD_PATHS is a list.
        if hasattr(config.LOAD_PATHS, 'split'):
            config.LOAD_PATHS = ','.join(load_path_list)
        else:
            config.LOAD_PATHS = load_path_list
    if options.assets_url is not None:
        config.ASSETS_URL = options.assets_url

    # Execution modes
    if options.test:
        run_tests()
    elif options.version:
        print_version()
    elif options.interactive:
        run_repl(options)
    elif options.watch:
        watch_sources(options)
    else:
        do_build(options, args)


def print_version():
    print(BUILD_INFO)


def run_tests():
    try:
        import pytest
    except ImportError:
        raise ImportError("You need py.test installed to run the test suite.")
    pytest.main("")  # don't let py.test re-consume our arguments


def do_build(options, args):
    if options.output is not None:
        output = open(options.output, 'wt')
    else:
        output = sys.stdout

    css = Scss(scss_opts={
        'style': options.style,
        'debug_info': options.debug_info,
    })
    if args:
        for path in args:
            output.write(css.compile(scss_file=path, is_sass=options.is_sass))
    else:
        output.write(css.compile(sys.stdin.read(), is_sass=options.is_sass))

    for f, t in profiling.items():
        sys.stderr.write("%s took %03fs" % (f, t))


def watch_sources(options):
    import time
    try:
        from watchdog.observers import Observer
        from watchdog.events import PatternMatchingEventHandler
    except ImportError:
        sys.stderr.write("Using watch functionality requires the `watchdog` library: http://pypi.python.org/pypi/watchdog/")
        sys.exit(1)
    if options.output and not os.path.isdir(options.output):
        sys.stderr.write("watch file output directory is invalid: '%s'" % (options.output))
        sys.exit(2)

    class ScssEventHandler(PatternMatchingEventHandler):
        def __init__(self, *args, **kwargs):
            super(ScssEventHandler, self).__init__(*args, **kwargs)
            self.css = Scss(scss_opts={
                'style': options.style,
                'debug_info': options.debug_info,
            })
            self.output = options.output
            self.suffix = options.suffix

        def is_valid(self, path):
            return os.path.isfile(path) and (path.endswith('.scss') or path.endswith('.sass')) and not os.path.basename(path).startswith('_')

        def process(self, path):
            if os.path.isdir(path):
                for f in os.listdir(path):
                    full = os.path.join(path, f)
                    if self.is_valid(full):
                        self.compile(full)
            elif self.is_valid(path):
                self.compile(path)

        def compile(self, src_path):
            fname = os.path.basename(src_path)
            if fname.endswith('.scss') or fname.endswith('.sass'):
                fname = fname[:-5]
                if self.suffix:
                    fname += '.' + self.suffix
                fname += '.css'
            else:
                # you didn't give me a file of the correct type!
                return False

            if self.output:
                dest_path = os.path.join(self.output, fname)
            else:
                dest_path = os.path.join(os.path.dirname(src_path), fname)

            print("Compiling %s => %s" % (src_path, dest_path))
            dest_file = open(dest_path, 'w')
            dest_file.write(self.css.compile(scss_file=src_path))

        def on_moved(self, event):
            super(ScssEventHandler, self).on_moved(event)
            self.process(event.dest_path)

        def on_created(self, event):
            super(ScssEventHandler, self).on_created(event)
            self.process(event.src_path)

        def on_modified(self, event):
            super(ScssEventHandler, self).on_modified(event)
            self.process(event.src_path)

    event_handler = ScssEventHandler(patterns=['*.scss', '*.sass'])
    observer = Observer()
    observer.schedule(event_handler, path=options.watch, recursive=options.recursive)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


@contextmanager
def readline_history(fn):
    try:
        import readline
    except ImportError:
        yield
        return

    try:
        readline.read_history_file(fn)
    except IOError:
        pass

    try:
        yield
    finally:
        try:
            readline.write_history_file(fn)
        except IOError:
            pass


def run_repl(is_sass=False):
    repl = SassRepl()

    with readline_history(os.path.expanduser('~/.scss-history')):
        print("Welcome to %s interactive shell" % (BUILD_INFO,))
        while True:
            try:
                in_ = raw_input('>>> ').strip()
                for output in repl(in_):
                    print(output)
            except (EOFError, KeyboardInterrupt):
                print("Bye!")
                return


class SassRepl(object):
    def __init__(self, is_sass=False):
        self.css = Scss()
        self.namespace = self.css.root_namespace
        self.options = self.css.scss_opts
        self.source_file = SourceFile.from_string('', '<shell>', line_numbers=False, is_sass=is_sass)
        self.calculator = Calculator(self.namespace)

    def __call__(self, s):
        from pprint import pformat

        if s in ('exit', 'quit'):
            raise KeyboardInterrupt

        for s in s.split(';'):
            s = self.source_file.prepare_source(s.strip())
            if not s:
                continue
            elif s.startswith('@'):
                scope = None
                properties = []
                children = deque()
                rule = SassRule(self.source_file, namespace=self.namespace, options=self.options, properties=properties)
                block = UnparsedBlock(rule, 1, s, None)
                code, name = (s.split(None, 1) + [''])[:2]
                if code == '@option':
                    self.css._settle_options(rule, children, scope, block)
                    continue
                elif code == '@import':
                    self.css._do_import(rule, children, scope, block)
                    continue
                elif code == '@include':
                    final_cont = ''
                    self.css._do_include(rule, children, scope, block)
                    code = self.css._print_properties(properties).rstrip('\n')
                    if code:
                        final_cont += code
                    if children:
                        self.css.children.extendleft(children)
                        self.css.parse_children()
                        code = self.css._create_css(self.css.rules).rstrip('\n')
                        if code:
                            final_cont += code
                    yield final_cont
                    continue
            elif s == 'ls' or s.startswith('show(') or s.startswith('show ') or s.startswith('ls(') or s.startswith('ls '):
                m = re.match(r'(?:show|ls)(\()?\s*([^,/\\) ]*)(?:[,/\\ ]([^,/\\ )]+))*(?(1)\))', s, re.IGNORECASE)
                if m:
                    name = m.group(2)
                    code = m.group(3)
                    name = name and name.strip().rstrip('s')  # remove last 's' as in functions
                    code = code and code.strip()
                    ns = self.namespace
                    if not name:
                        yield pformat(sorted(['vars', 'options', 'mixins', 'functions']))
                    elif name in ('v', 'var', 'variable'):
                        variables = dict(ns._variables)
                        if code == '*':
                            pass
                        elif code:
                            variables = dict((k, v) for k, v in variables.items() if code in k)
                        else:
                            variables = dict((k, v) for k, v in variables.items() if not k.startswith('$--'))
                        yield pformat(variables)

                    elif name in ('o', 'opt', 'option'):
                        opts = self.options
                        if code == '*':
                            pass
                        elif code:
                            opts = dict((k, v) for k, v in opts.items() if code in k)
                        else:
                            opts = dict((k, v) for k, v in opts.items() if not k.startswith('@'))
                        yield pformat(opts)

                    elif name in ('m', 'mix', 'mixin', 'f', 'func', 'funct', 'function'):
                        if name.startswith('m'):
                            funcs = dict(ns._mixins)
                        elif name.startswith('f'):
                            funcs = dict(ns._functions)
                        if code == '*':
                            pass
                        elif code:
                            funcs = dict((k, v) for k, v in funcs.items() if code in k[0])
                        else:
                            pass
                        # TODO print source when possible
                        yield pformat(funcs)
                    continue
            elif s.startswith('$') and (':' in s or '=' in s):
                prop, value = [a.strip() for a in _prop_split_re.split(s, 1)]
                prop = self.calculator.do_glob_math(prop)
                value = self.calculator.calculate(value)
                self.namespace.set_variable(prop, value)
                continue

            # TODO respect compress?
            try:
                yield(self.calculator.calculate(s).render())
            except (SyntaxError, SassEvaluationError) as e:
                print("%s" % e, file=sys.stderr)


if __name__ == "__main__":
    main()

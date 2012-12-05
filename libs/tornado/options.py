#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A command line parsing module that lets modules define their own options.

Each module defines its own options which are added to the global
option namespace, e.g.::

    from tornado.options import define, options

    define("mysql_host", default="127.0.0.1:3306", help="Main user DB")
    define("memcache_hosts", default="127.0.0.1:11011", multiple=True,
           help="Main user memcache servers")

    def connect():
        db = database.Connection(options.mysql_host)
        ...

The main() method of your application does not need to be aware of all of
the options used throughout your program; they are all automatically loaded
when the modules are loaded.  However, all modules that define options
must have been imported before the command line is parsed.

Your main() method can parse the command line or parse a config file with
either::

    tornado.options.parse_command_line()
    # or
    tornado.options.parse_config_file("/etc/server.conf")

Command line formats are what you would expect ("--myoption=myvalue").
Config files are just Python files. Global names become options, e.g.::

    myoption = "myvalue"
    myotheroption = "myothervalue"

We support datetimes, timedeltas, ints, and floats (just pass a 'type'
kwarg to define). We also accept multi-value options. See the documentation
for define() below.

`tornado.options.options` is a singleton instance of `OptionParser`, and
the top-level functions in this module (`define`, `parse_command_line`, etc)
simply call methods on it.  You may create additional `OptionParser`
instances to define isolated sets of options, such as for subcommands.
"""

from __future__ import absolute_import, division, with_statement

import datetime
import re
import sys
import os
import textwrap

from tornado.escape import _unicode
from tornado.log import define_logging_options
from tornado import stack_context


class Error(Exception):
    """Exception raised by errors in the options module."""
    pass


class OptionParser(object):
    """A collection of options, a dictionary with object-like access.

    Normally accessed via static functions in the `tornado.options` module,
    which reference a global instance.
    """
    def __init__(self):
        # we have to use self.__dict__ because we override setattr.
        self.__dict__['_options'] = {}
        self.__dict__['_parse_callbacks'] = []
        self.define("help", type=bool, help="show this help information",
                    callback=self._help_callback)

    def __getattr__(self, name):
        if isinstance(self._options.get(name), _Option):
            return self._options[name].value()
        raise AttributeError("Unrecognized option %r" % name)

    def __setattr__(self, name, value):
        if isinstance(self._options.get(name), _Option):
            return self._options[name].set(value)
        raise AttributeError("Unrecognized option %r" % name)

    def define(self, name, default=None, type=None, help=None, metavar=None,
               multiple=False, group=None, callback=None):
        """Defines a new command line option.

        If type is given (one of str, float, int, datetime, or timedelta)
        or can be inferred from the default, we parse the command line
        arguments based on the given type. If multiple is True, we accept
        comma-separated values, and the option value is always a list.

        For multi-value integers, we also accept the syntax x:y, which
        turns into range(x, y) - very useful for long integer ranges.

        help and metavar are used to construct the automatically generated
        command line help string. The help message is formatted like::

           --name=METAVAR      help string

        group is used to group the defined options in logical
        groups. By default, command line options are grouped by the
        file in which they are defined.

        Command line option names must be unique globally. They can be parsed
        from the command line with parse_command_line() or parsed from a
        config file with parse_config_file.

        If a callback is given, it will be run with the new value whenever
        the option is changed.  This can be used to combine command-line
        and file-based options::

            define("config", type=str, help="path to config file",
                   callback=lambda path: parse_config_file(path, final=False))

        With this definition, options in the file specified by ``--config`` will
        override options set earlier on the command line, but can be overridden
        by later flags.
        """
        if name in self._options:
            raise Error("Option %r already defined in %s", name,
                        self._options[name].file_name)
        frame = sys._getframe(0)
        options_file = frame.f_code.co_filename
        file_name = frame.f_back.f_code.co_filename
        if file_name == options_file:
            file_name = ""
        if type is None:
            if not multiple and default is not None:
                type = default.__class__
            else:
                type = str
        if group:
            group_name = group
        else:
            group_name = file_name
        self._options[name] = _Option(name, file_name=file_name,
                                      default=default, type=type, help=help,
                                      metavar=metavar, multiple=multiple,
                                      group_name=group_name,
                                      callback=callback)

    def parse_command_line(self, args=None, final=True):
        """Parses all options given on the command line (defaults to sys.argv).

        Note that args[0] is ignored since it is the program name in sys.argv.

        We return a list of all arguments that are not parsed as options.

        If ``final`` is ``False``, parse callbacks will not be run.
        This is useful for applications that wish to combine configurations
        from multiple sources.
        """
        if args is None:
            args = sys.argv
        remaining = []
        for i in xrange(1, len(args)):
            # All things after the last option are command line arguments
            if not args[i].startswith("-"):
                remaining = args[i:]
                break
            if args[i] == "--":
                remaining = args[i + 1:]
                break
            arg = args[i].lstrip("-")
            name, equals, value = arg.partition("=")
            name = name.replace('-', '_')
            if not name in self._options:
                self.print_help()
                raise Error('Unrecognized command line option: %r' % name)
            option = self._options[name]
            if not equals:
                if option.type == bool:
                    value = "true"
                else:
                    raise Error('Option %r requires a value' % name)
            option.parse(value)

        if final:
            self.run_parse_callbacks()

        return remaining

    def parse_config_file(self, path, final=True):
        """Parses and loads the Python config file at the given path.

        If ``final`` is ``False``, parse callbacks will not be run.
        This is useful for applications that wish to combine configurations
        from multiple sources.
        """
        config = {}
        execfile(path, config, config)
        for name in config:
            if name in self._options:
                self._options[name].set(config[name])

        if final:
            self.run_parse_callbacks()

    def print_help(self, file=None):
        """Prints all the command line options to stderr (or another file)."""
        if file is None:
            file = sys.stderr
        print >> file, "Usage: %s [OPTIONS]" % sys.argv[0]
        print >> file, "\nOptions:\n"
        by_group = {}
        for option in self._options.itervalues():
            by_group.setdefault(option.group_name, []).append(option)

        for filename, o in sorted(by_group.items()):
            if filename:
                print >> file, "\n%s options:\n" % os.path.normpath(filename)
            o.sort(key=lambda option: option.name)
            for option in o:
                prefix = option.name
                if option.metavar:
                    prefix += "=" + option.metavar
                description = option.help or ""
                if option.default is not None and option.default != '':
                    description += " (default %s)" % option.default
                lines = textwrap.wrap(description, 79 - 35)
                if len(prefix) > 30 or len(lines) == 0:
                    lines.insert(0, '')
                print >> file, "  --%-30s %s" % (prefix, lines[0])
                for line in lines[1:]:
                    print >> file, "%-34s %s" % (' ', line)
        print >> file

    def _help_callback(self, value):
        if value:
            self.print_help()
            sys.exit(0)

    def add_parse_callback(self, callback):
        """Adds a parse callback, to be invoked when option parsing is done."""
        self._parse_callbacks.append(stack_context.wrap(callback))

    def run_parse_callbacks(self):
        for callback in self._parse_callbacks:
            callback()

    def mockable(self):
        """Returns a wrapper around self that is compatible with `mock.patch`.

        The `mock.patch` function (included in the standard library
        `unittest.mock` package since Python 3.3, or in the
        third-party `mock` package for older versions of Python) is
        incompatible with objects like ``options`` that override
        ``__getattr__`` and ``__setattr__``.  This function returns an
        object that can be used with `mock.patch.object` to modify
        option values::

            with mock.patch.object(options.mockable(), 'name', value):
                assert options.name == value
        """
        return _Mockable(self)

class _Mockable(object):
    """`mock.patch` compatible wrapper for `OptionParser`.

    As of ``mock`` version 1.0.1, when an object uses ``__getattr__``
    hooks instead of ``__dict__``, ``patch.__exit__`` tries to delete
    the attribute it set instead of setting a new one (assuming that
    the object does not catpure ``__setattr__``, so the patch
    created a new attribute in ``__dict__``).

    _Mockable's getattr and setattr pass through to the underlying
    OptionParser, and delattr undoes the effect of a previous setattr.
    """
    def __init__(self, options):
        # Modify __dict__ directly to bypass __setattr__
        self.__dict__['_options'] = options
        self.__dict__['_originals'] = {}

    def __getattr__(self, name):
        return getattr(self._options, name)

    def __setattr__(self, name, value):
        assert name not in self._originals, "don't reuse mockable objects"
        self._originals[name] = getattr(self._options, name)
        setattr(self._options, name, value)

    def __delattr__(self, name):
        setattr(self._options, name, self._originals.pop(name))

class _Option(object):
    def __init__(self, name, default=None, type=basestring, help=None,
                 metavar=None, multiple=False, file_name=None, group_name=None,
                 callback=None):
        if default is None and multiple:
            default = []
        self.name = name
        self.type = type
        self.help = help
        self.metavar = metavar
        self.multiple = multiple
        self.file_name = file_name
        self.group_name = group_name
        self.callback = callback
        self.default = default
        self._value = None

    def value(self):
        return self.default if self._value is None else self._value

    def parse(self, value):
        _parse = {
            datetime.datetime: self._parse_datetime,
            datetime.timedelta: self._parse_timedelta,
            bool: self._parse_bool,
            basestring: self._parse_string,
        }.get(self.type, self.type)
        if self.multiple:
            self._value = []
            for part in value.split(","):
                if self.type in (int, long):
                    # allow ranges of the form X:Y (inclusive at both ends)
                    lo, _, hi = part.partition(":")
                    lo = _parse(lo)
                    hi = _parse(hi) if hi else lo
                    self._value.extend(range(lo, hi + 1))
                else:
                    self._value.append(_parse(part))
        else:
            self._value = _parse(value)
        if self.callback is not None:
            self.callback(self._value)
        return self.value()

    def set(self, value):
        if self.multiple:
            if not isinstance(value, list):
                raise Error("Option %r is required to be a list of %s" %
                            (self.name, self.type.__name__))
            for item in value:
                if item != None and not isinstance(item, self.type):
                    raise Error("Option %r is required to be a list of %s" %
                                (self.name, self.type.__name__))
        else:
            if value != None and not isinstance(value, self.type):
                raise Error("Option %r is required to be a %s (%s given)" %
                            (self.name, self.type.__name__, type(value)))
        self._value = value
        if self.callback is not None:
            self.callback(self._value)

    # Supported date/time formats in our options
    _DATETIME_FORMATS = [
        "%a %b %d %H:%M:%S %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y%m%d %H:%M:%S",
        "%Y%m%d %H:%M",
        "%Y-%m-%d",
        "%Y%m%d",
        "%H:%M:%S",
        "%H:%M",
    ]

    def _parse_datetime(self, value):
        for format in self._DATETIME_FORMATS:
            try:
                return datetime.datetime.strptime(value, format)
            except ValueError:
                pass
        raise Error('Unrecognized date/time format: %r' % value)

    _TIMEDELTA_ABBREVS = [
        ('hours', ['h']),
        ('minutes', ['m', 'min']),
        ('seconds', ['s', 'sec']),
        ('milliseconds', ['ms']),
        ('microseconds', ['us']),
        ('days', ['d']),
        ('weeks', ['w']),
    ]

    _TIMEDELTA_ABBREV_DICT = dict(
        (abbrev, full) for full, abbrevs in _TIMEDELTA_ABBREVS
        for abbrev in abbrevs)

    _FLOAT_PATTERN = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'

    _TIMEDELTA_PATTERN = re.compile(
        r'\s*(%s)\s*(\w*)\s*' % _FLOAT_PATTERN, re.IGNORECASE)

    def _parse_timedelta(self, value):
        try:
            sum = datetime.timedelta()
            start = 0
            while start < len(value):
                m = self._TIMEDELTA_PATTERN.match(value, start)
                if not m:
                    raise Exception()
                num = float(m.group(1))
                units = m.group(2) or 'seconds'
                units = self._TIMEDELTA_ABBREV_DICT.get(units, units)
                sum += datetime.timedelta(**{units: num})
                start = m.end()
            return sum
        except Exception:
            raise

    def _parse_bool(self, value):
        return value.lower() not in ("false", "0", "f")

    def _parse_string(self, value):
        return _unicode(value)


options = OptionParser()
"""Global options object.

All defined options are available as attributes on this object.
"""


def define(name, default=None, type=None, help=None, metavar=None,
           multiple=False, group=None, callback=None):
    """Defines an option in the global namespace.

    See `OptionParser.define`.
    """
    return options.define(name, default=default, type=type, help=help,
                          metavar=metavar, multiple=multiple, group=group,
                          callback=callback)


def parse_command_line(args=None, final=True):
    """Parses global options from the command line.

    See `OptionParser.parse_command_line`.
    """
    return options.parse_command_line(args, final=final)


def parse_config_file(path, final=True):
    """Parses global options from a config file.

    See `OptionParser.parse_config_file`.
    """
    return options.parse_config_file(path, final=final)


def print_help(file=None):
    """Prints all the command line options to stderr (or another file).

    See `OptionParser.print_help`.
    """
    return options.print_help(file)

def add_parse_callback(callback):
    """Adds a parse callback, to be invoked when option parsing is done.

    See `OptionParser.add_parse_callback`
    """
    options.add_parse_callback(callback)


# Default options
define_logging_options(options)

# logr - Simple python logging wrapper
# Packed by Dean Gardiner <gardiner91@gmail.com>
#
# File part of:
# rdio-sock - Rdio WebSocket Library
# Copyright (C) 2013  fzza- <fzzzzzzzza@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import inspect
import logging
import os
import sys

IGNORE = ()
PY3 = sys.version_info[0] == 3


class Logr(object):
    loggers = {}
    handler = None

    trace_origin = False
    name = "Logr"

    @staticmethod
    def configure(level=logging.WARNING, handler=None, formatter=None, trace_origin=False, name="Logr"):
        """Configure Logr

        @param handler: Logger message handler
        @type handler: logging.Handler or None

        @param formatter: Logger message Formatter
        @type formatter: logging.Formatter or None
        """
        if formatter is None:
            formatter = LogrFormatter()

        if handler is None:
            handler = logging.StreamHandler()

        handler.setFormatter(formatter)
        handler.setLevel(level)
        Logr.handler = handler

        Logr.trace_origin = trace_origin
        Logr.name = name

    @staticmethod
    def configure_check():
        if Logr.handler is None:
            Logr.configure()

    @staticmethod
    def _get_name_from_path(filename):
        try:
            return os.path.splitext(os.path.basename(filename))[0]
        except TypeError:
            return "<unknown>"

    @staticmethod
    def get_frame_class(frame):
        if len(frame.f_code.co_varnames) <= 0:
            return None

        farg = frame.f_code.co_varnames[0]

        if farg not in frame.f_locals:
            return None

        if farg == 'self':
            return frame.f_locals[farg].__class__

        if farg == 'cls':
            return frame.f_locals[farg]

        return None


    @staticmethod
    def get_logger_name():
        if not Logr.trace_origin:
            return Logr.name

        stack = inspect.stack()

        for x in xrange_six(len(stack)):
            frame = stack[x][0]
            name = None

            # Try find name of function defined inside a class
            frame_class = Logr.get_frame_class(frame)

            if frame_class:
                class_name = frame_class.__name__
                module_name = frame_class.__module__

                if module_name != '__main__':
                    name = module_name + '.' + class_name
                else:
                    name = class_name

            # Try find name of function defined outside of a class
            if name is None:
                if frame.f_code.co_name in frame.f_globals:
                    name = frame.f_globals.get('__name__')
                    if name == '__main__':
                        name = Logr._get_name_from_path(frame.f_globals.get('__file__'))
                    name = name
                elif frame.f_code.co_name == '<module>':
                    name = Logr._get_name_from_path(frame.f_globals.get('__file__'))

            if name is not None and name not in IGNORE:
                return name

        return ""

    @staticmethod
    def get_logger():
        """Get or create logger (if it does not exist)

        @rtype: RootLogger
        """
        name = Logr.get_logger_name()
        if name not in Logr.loggers:
            Logr.configure_check()
            Logr.loggers[name] = logging.Logger(name)
            Logr.loggers[name].addHandler(Logr.handler)
        return Logr.loggers[name]

    @staticmethod
    def debug(msg, *args, **kwargs):
        Logr.get_logger().debug(msg, *args, **kwargs)

    @staticmethod
    def info(msg, *args, **kwargs):
        Logr.get_logger().info(msg, *args, **kwargs)

    @staticmethod
    def warning(msg, *args, **kwargs):
        Logr.get_logger().warning(msg, *args, **kwargs)

    warn = warning

    @staticmethod
    def error(msg, *args, **kwargs):
        Logr.get_logger().error(msg, *args, **kwargs)

    @staticmethod
    def exception(msg, *args, **kwargs):
        Logr.get_logger().exception(msg, *args, **kwargs)

    @staticmethod
    def critical(msg, *args, **kwargs):
        Logr.get_logger().critical(msg, *args, **kwargs)

    fatal = critical

    @staticmethod
    def log(level, msg, *args, **kwargs):
        Logr.get_logger().log(level, msg, *args, **kwargs)


class LogrFormatter(logging.Formatter):
    LENGTH_NAME = 32
    LENGTH_LEVEL_NAME = 5

    def __init__(self, fmt=None, datefmt=None):
        if sys.version_info[:2] > (2,6):
            super(LogrFormatter, self).__init__(fmt, datefmt)
        else:
            logging.Formatter.__init__(self, fmt, datefmt)

    def usesTime(self):
        return True

    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        s = "%(asctime)s    %(name)s    %(levelname)s    %(message)s" % {
            'asctime': record.asctime,
            'name': record.name[-self.LENGTH_NAME:].rjust(self.LENGTH_NAME, ' '),
            'levelname': record.levelname[:self.LENGTH_LEVEL_NAME].ljust(self.LENGTH_LEVEL_NAME, ' '),
            'message': record.message
        }

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s += "\n"
            try:
                s += record.exc_text
            except UnicodeError:
                s = s + record.exc_text.decode(sys.getfilesystemencoding(),
                                               'replace')
        return s


def xrange_six(start, stop=None, step=None):
    if stop is not None and step is not None:
        if PY3:
            return range(start, stop, step)
        else:
            return xrange(start, stop, step)
    else:
        if PY3:
            return range(start)
        else:
            return xrange(start)

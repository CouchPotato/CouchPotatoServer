#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Smewt - A smart collection manager
# Copyright (c) 2011 Nicolas Wack <wackou@gmail.com>
#
# Smewt is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Smewt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
import sys

GREEN_FONT = "\x1B[0;32m"
YELLOW_FONT = "\x1B[0;33m"
BLUE_FONT = "\x1B[0;34m"
RED_FONT = "\x1B[0;31m"
RESET_FONT = "\x1B[0m"


def setupLogging(colored=True):
    """Set up a nice colored logger as the main application logger."""

    class SimpleFormatter(logging.Formatter):
        def __init__(self):
            self.fmt = '%(levelname)-8s %(module)s:%(funcName)s -- %(message)s'
            logging.Formatter.__init__(self, self.fmt)

    class ColoredFormatter(logging.Formatter):
        def __init__(self):
            self.fmt = ('%(levelname)-8s ' +
                        BLUE_FONT + '%(name)s:%(funcName)s' +
                        RESET_FONT + ' -- %(message)s')
            logging.Formatter.__init__(self, self.fmt)

        def format(self, record):
            result = logging.Formatter.format(self, record)
            if record.levelno in (logging.DEBUG, logging.INFO):
                return GREEN_FONT + result
            elif record.levelno == logging.WARNING:
                return YELLOW_FONT + result
            else:
                return RED_FONT + result

    ch = logging.StreamHandler()
    if colored and sys.platform != 'win32':
        ch.setFormatter(ColoredFormatter())
    else:
        ch.setFormatter(SimpleFormatter())
    logging.getLogger().addHandler(ch)

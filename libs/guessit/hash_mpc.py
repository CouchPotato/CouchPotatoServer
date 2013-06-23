#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2011 Nicolas Wack <wackou@gmail.com>
#
# GuessIt is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# GuessIt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import unicode_literals
import struct
import os


def hash_file(filename):
    """This function is taken from:
    http://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes
    and is licensed under the GPL."""

    longlongformat = 'q'  # long long
    bytesize = struct.calcsize(longlongformat)

    f = open(filename, "rb")

    filesize = os.path.getsize(filename)
    hash_value = filesize

    if filesize < 65536 * 2:
        raise Exception("SizeError: size is %d, should be > 132K..." % filesize)

    for x in range(65536 / bytesize):
        buf = f.read(bytesize)
        (l_value,) = struct.unpack(longlongformat, buf)
        hash_value += l_value
        hash_value = hash_value & 0xFFFFFFFFFFFFFFFF #to remain as 64bit number

    f.seek(max(0, filesize - 65536), 0)
    for x in range(65536 / bytesize):
        buf = f.read(bytesize)
        (l_value,) = struct.unpack(longlongformat, buf)
        hash_value += l_value
        hash_value = hash_value & 0xFFFFFFFFFFFFFFFF

    f.close()

    return "%016x" % hash_value

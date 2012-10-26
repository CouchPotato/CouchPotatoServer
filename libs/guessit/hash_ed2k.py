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
from guessit import s, to_hex
import hashlib
import os.path


def hash_file(filename):
    """Returns the ed2k hash of a given file.

    >>> s(hash_file('tests/dummy.srt'))
    'ed2k://|file|dummy.srt|44|1CA0B9DED3473B926AA93A0A546138BB|/'
    """
    return 'ed2k://|file|%s|%d|%s|/' % (os.path.basename(filename),
                                        os.path.getsize(filename),
                                        hash_filehash(filename).upper())


def hash_filehash(filename):
    """Returns the ed2k hash of a given file.

    This function is taken from:
    http://www.radicand.org/blog/orz/2010/2/21/edonkey2000-hash-in-python/
    """
    md4 = hashlib.new('md4').copy

    def gen(f):
        while True:
            x = f.read(9728000)
            if x:
                yield x
            else:
                return

    def md4_hash(data):
        m = md4()
        m.update(data)
        return m

    with open(filename, 'rb') as f:
        a = gen(f)
        hashes = [md4_hash(data).digest() for data in a]
        if len(hashes) == 1:
            return to_hex(hashes[0])
        else:
            return md4_hash(reduce(lambda a, d: a + d, hashes, "")).hexd

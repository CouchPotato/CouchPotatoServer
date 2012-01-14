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

import os.path


def split_path(path):
    r"""Splits the given path into the list of folders and the filename (or the
    last folder if you gave it a folder path.

    If the given path was an absolute path, the first element will always be:
     - the '/' root folder on Unix systems
     - the drive letter on Windows systems (eg: r'C:\')

    >>> split_path('/usr/bin/smewt')
    ['/', 'usr', 'bin', 'smewt']

    >>> split_path('relative_path/to/my_folder/')
    ['relative_path', 'to', 'my_folder']

    >>> split_path(r'C:\Program Files\Smewt\smewt.exe')
    ['C:\\', 'Program Files', 'Smewt', 'smewt.exe']

    >>> split_path(r'Documents and Settings\User\config\\')
    ['Documents and Settings', 'User', 'config']

    """
    result = []
    while True:
        head, tail = os.path.split(path)

        # on Unix systems, the root folder is '/'
        if head == '/' and tail == '':
            return [ '/' ] + result

        # on Windows, the root folder is a drive letter (eg: 'C:\')
        if len(head) == 3 and head[1:] == ':\\' and tail == '':
            return [ head ] + result

        if head == '' and tail == '':
            return result

        # we just split a directory ending with '/', so tail is empty
        if not tail:
            path = head
            continue

        result = [ tail ] + result
        path = head


def split_path_components(filename):
    """Returns the filename split into [ dir*, basename, ext ]."""
    result = split_path(filename)
    basename = result.pop(-1)
    return result + list(os.path.splitext(basename))


def file_in_same_dir(ref_file, desired_file):
    """Return the path for a file in the same dir as a given reference file.

    >>> file_in_same_dir('~/smewt/smewt.db', 'smewt.settings')
    '~/smewt/smewt.settings'

    """
    return os.path.join(*(split_path(ref_file)[:-1] + [ desired_file ]))

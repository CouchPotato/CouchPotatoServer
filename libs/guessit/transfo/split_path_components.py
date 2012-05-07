#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2012 Nicolas Wack <wackou@gmail.com>
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

from guessit import fileutils
import os.path
import logging

log = logging.getLogger(__name__)


def process(mtree):
    """Returns the filename split into [ dir*, basename, ext ]."""
    components = fileutils.split_path(mtree.value)
    basename = components.pop(-1)
    components += list(os.path.splitext(basename))
    components[-1] = components[-1][1:] # remove the '.' from the extension

    mtree.split_on_components(components)

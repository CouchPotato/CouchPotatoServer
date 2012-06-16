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

from guessit.textutils import find_first_level_groups
from guessit.patterns import group_delimiters
import logging

log = logging.getLogger(__name__)


def process(mtree):
    """return the string split into explicit groups, that is, those either
    between parenthese, square brackets or curly braces, and those separated
    by a dash."""
    for c in mtree.children:
        groups = find_first_level_groups(c.value, group_delimiters[0])
        for delimiters in group_delimiters:
            flatten = lambda l, x: l + find_first_level_groups(x, delimiters)
            groups = reduce(flatten, groups, [])

        # do not do this at this moment, it is not strong enough and can break other
        # patterns, such as dates, etc...
        #groups = reduce(lambda l, x: l + x.split('-'), groups, [])

        c.split_on_components(groups)

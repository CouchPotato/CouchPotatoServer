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

from __future__ import unicode_literals
from guessit.country import Country
from guessit import Guess
import logging

log = logging.getLogger(__name__)

# list of common words which could be interpreted as countries, but which
# are far too common to be able to say they represent a country
country_common_words = frozenset([ 'bt', 'bb' ])

def process(mtree):
    for node in mtree.unidentified_leaves():
        if len(node.node_idx) == 2:
            c = node.value[1:-1].lower()
            if c in country_common_words:
                continue

            # only keep explicit groups (enclosed in parentheses/brackets)
            if node.value[0] + node.value[-1] not in ['()', '[]', '{}']:
                continue

            try:
                country = Country(c, strict=True)
            except ValueError:
                continue

            node.guess = Guess(country=country, confidence=1.0, raw=c)

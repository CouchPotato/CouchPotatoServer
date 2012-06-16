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

from guessit.patterns import sep
import re
import logging

log = logging.getLogger(__name__)


def process(mtree):
    for node in mtree.unidentified_leaves():
        indices = []

        didx = 0
        pattern = re.compile(sep + '-' + sep)
        match = pattern.search(node.value)
        while match:
            span = match.span()
            indices.extend([ span[0], span[1] ])
            match = pattern.search(node.value, span[1])

        didx = node.value.find('-')
        while didx > 0:
            if (didx > 10 and
                (didx - 1 not in indices and
                 didx + 2 not in indices)):

                indices.extend([ didx, didx + 1 ])

            didx = node.value.find('-', didx + 1)

        if indices:
            node.partition(indices)

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
from guessit.transfo import found_property
import logging

log = logging.getLogger(__name__)


def process(mtree):
    def previous_group(g):
        for leaf in mtree.unidentified_leaves()[::-1]:
            if leaf.node_idx < g.node_idx:
                return leaf

    def next_group(g):
        for leaf in mtree.unidentified_leaves():
            if leaf.node_idx > g.node_idx:
                return leaf

    def same_group(g1, g2):
        return g1.node_idx[:2] == g2.node_idx[:2]

    bonus = [ node for node in mtree.leaves() if 'bonusNumber' in node.guess ]
    if bonus:
        bonusTitle = next_group(bonus[0])
        if same_group(bonusTitle, bonus[0]):
            found_property(bonusTitle, 'bonusTitle', 0.8)

    filmNumber = [ node for node in mtree.leaves()
                   if 'filmNumber' in node.guess ]
    if filmNumber:
        filmSeries = previous_group(filmNumber[0])
        found_property(filmSeries, 'filmSeries', 0.9)

        title = next_group(filmNumber[0])
        found_property(title, 'title', 0.9)

    season = [ node for node in mtree.leaves() if 'season' in node.guess ]
    if season and 'bonusNumber' in mtree.info:
        series = previous_group(season[0])
        if same_group(series, season[0]):
            found_property(series, 'series', 0.9)

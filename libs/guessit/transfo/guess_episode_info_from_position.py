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
from guessit.patterns import non_episode_title, unlikely_series
import logging

log = logging.getLogger(__name__)


def match_from_epnum_position(mtree, node):
    epnum_idx = node.node_idx

    # a few helper functions to be able to filter using high-level semantics
    def before_epnum_in_same_pathgroup():
        return [ leaf for leaf in mtree.unidentified_leaves()
                 if (leaf.node_idx[0] == epnum_idx[0] and
                     leaf.node_idx[1:] < epnum_idx[1:]) ]

    def after_epnum_in_same_pathgroup():
        return [ leaf for leaf in mtree.unidentified_leaves()
                 if (leaf.node_idx[0] == epnum_idx[0] and
                     leaf.node_idx[1:] > epnum_idx[1:]) ]

    def after_epnum_in_same_explicitgroup():
        return [ leaf for leaf in mtree.unidentified_leaves()
                 if (leaf.node_idx[:2] == epnum_idx[:2] and
                     leaf.node_idx[2:] > epnum_idx[2:]) ]

    # epnumber is the first group and there are only 2 after it in same
    # path group
    # -> series title - episode title
    title_candidates = [ n for n in after_epnum_in_same_pathgroup()
                         if n.clean_value.lower() not in non_episode_title ]
    if ('title' not in mtree.info and                # no title
        before_epnum_in_same_pathgroup() == [] and   # no groups before
        len(title_candidates) == 2):                 # only 2 groups after

        found_property(title_candidates[0], 'series', confidence=0.4)
        found_property(title_candidates[1], 'title', confidence=0.4)
        return

    # if we have at least 1 valid group before the episodeNumber, then it's
    # probably the series name
    series_candidates = before_epnum_in_same_pathgroup()
    if len(series_candidates) >= 1:
        found_property(series_candidates[0], 'series', confidence=0.7)

    # only 1 group after (in the same path group) and it's probably the
    # episode title
    title_candidates = [ n for n in after_epnum_in_same_pathgroup()
                         if n.clean_value.lower() not in non_episode_title ]

    if len(title_candidates) == 1:
        found_property(title_candidates[0], 'title', confidence=0.5)
        return
    else:
        # try in the same explicit group, with lower confidence
        title_candidates = [ n for n in after_epnum_in_same_explicitgroup()
                             if n.clean_value.lower() not in non_episode_title
                             ]
        if len(title_candidates) == 1:
            found_property(title_candidates[0], 'title', confidence=0.4)
            return
        elif len(title_candidates) > 1:
            found_property(title_candidates[0], 'title', confidence=0.3)
            return

    # get the one with the longest value
    title_candidates = [ n for n in after_epnum_in_same_pathgroup()
                         if n.clean_value.lower() not in non_episode_title ]
    if title_candidates:
        maxidx = -1
        maxv = -1
        for i, c in enumerate(title_candidates):
            if len(c.clean_value) > maxv:
                maxidx = i
                maxv = len(c.clean_value)
        found_property(title_candidates[maxidx], 'title', confidence=0.3)


def process(mtree):
    eps = [node for node in mtree.leaves() if 'episodeNumber' in node.guess]
    if eps:
        match_from_epnum_position(mtree, eps[0])

    else:
        # if we don't have the episode number, but at least 2 groups in the
        # basename, then it's probably series - eptitle
        basename = mtree.node_at((-2,))
        title_candidates = [ n for n in basename.unidentified_leaves()
                             if n.clean_value.lower() not in non_episode_title
                             ]

        if len(title_candidates) >= 2:
            found_property(title_candidates[0], 'series', 0.4)
            found_property(title_candidates[1], 'title', 0.4)
        elif len(title_candidates) == 1:
            # but if there's only one candidate, it's probably the series name
            found_property(title_candidates[0], 'series', 0.4)

    # if we only have 1 remaining valid group in the folder containing the
    # file, then it's likely that it is the series name
    try:
        series_candidates = mtree.node_at((-3,)).unidentified_leaves()
    except ValueError:
        series_candidates = []

    if len(series_candidates) == 1:
        found_property(series_candidates[0], 'series', 0.3)

    # if there's a path group that only contains the season info, then the
    # previous one is most likely the series title (ie: ../series/season X/..)
    eps = [ node for node in mtree.nodes()
            if 'season' in node.guess and 'episodeNumber' not in node.guess ]

    if eps:
        previous = [ node for node in mtree.unidentified_leaves()
                     if node.node_idx[0] == eps[0].node_idx[0] - 1 ]
        if len(previous) == 1:
            found_property(previous[0], 'series', 0.5)

    # reduce the confidence of unlikely series
    for node in mtree.nodes():
        if 'series' in node.guess:
            if node.guess['series'].lower() in unlikely_series:
                new_confidence = node.guess.confidence('series') * 0.5
                node.guess.set_confidence('series', new_confidence)

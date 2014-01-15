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
from guessit import Guess
from guessit.transfo import SingleNodeGuesser
from guessit.patterns import weak_episode_rexps
import re
import logging

log = logging.getLogger(__name__)


def guess_weak_episodes_rexps(string, node):
    if 'episodeNumber' in node.root.info:
        return None, None

    for rexp, span_adjust in weak_episode_rexps:
        match = re.search(rexp, string, re.IGNORECASE)
        if match:
            metadata = match.groupdict()
            span = (match.start() + span_adjust[0],
                    match.end() + span_adjust[1])

            epnum = int(metadata['episodeNumber'])
            if epnum > 100:
                season, epnum = epnum // 100, epnum % 100
                # episodes which have a season > 25 are most likely errors
                # (Simpsons is at 23!)
                if season > 25:
                    continue
                return Guess({ 'season': season,
                               'episodeNumber': epnum },
                             confidence=0.6), span
            else:
                return Guess(metadata, confidence=0.3), span

    return None, None


guess_weak_episodes_rexps.use_node = True


def process(mtree):
    SingleNodeGuesser(guess_weak_episodes_rexps, 0.6, log).process(mtree)

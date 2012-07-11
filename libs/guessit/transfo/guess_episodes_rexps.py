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

from guessit import Guess
from guessit.transfo import SingleNodeGuesser
from guessit.patterns import episode_rexps
import re
import logging

log = logging.getLogger(__name__)

def number_list(s):
    return re.sub('[^0-9]+', ' ', s).split()

def guess_episodes_rexps(string):
    for rexp, confidence, span_adjust in episode_rexps:
        match = re.search(rexp, string, re.IGNORECASE)
        if match:
            result = (Guess(match.groupdict(), confidence=confidence),
                      (match.start() + span_adjust[0],
                       match.end() + span_adjust[1]))
            # episodes which have a season > 25 are most likely errors
            # (Simpsons is at 23!)
            if int(result[0].get('season', 0)) > 25:
                continue

            # decide whether we have only a single episode number or an
            # episode list
            if result[0].get('episodeNumber'):
                eplist = number_list(result[0]['episodeNumber'])
                result[0].set('episodeNumber', int(eplist[0]), confidence=confidence)

                if len(eplist) > 1:
                    result[0].set('episodeList', map(int, eplist), confidence=confidence)

            return result

    return None, None


def process(mtree):
    SingleNodeGuesser(guess_episodes_rexps, None, log).process(mtree)

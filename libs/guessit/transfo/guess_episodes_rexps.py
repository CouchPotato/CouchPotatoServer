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
from guessit.patterns import episode_rexps
import re
import logging

log = logging.getLogger(__name__)

def number_list(s):
    l = [ int(n) for n in re.sub('[^0-9]+', ' ', s).split() ]

    if len(l) == 2:
        # it is an episode interval, return all numbers in between
        return range(l[0], l[1]+1)

    return l

def guess_episodes_rexps(string):
    for rexp, confidence, span_adjust in episode_rexps:
        match = re.search(rexp, string, re.IGNORECASE)
        if match:
            span = (match.start() + span_adjust[0], 
                    match.end() + span_adjust[1])
            guess = Guess(match.groupdict(), confidence=confidence, raw=string[span[0]:span[1]])

            # decide whether we have only a single episode number or an
            # episode list
            if guess.get('episodeNumber'):
                eplist = number_list(guess['episodeNumber'])
                guess.set('episodeNumber', eplist[0], confidence=confidence, raw=string[span[0]:span[1]])

                if len(eplist) > 1:
                    guess.set('episodeList', eplist, confidence=confidence, raw=string[span[0]:span[1]])

            if guess.get('bonusNumber'):
                eplist = number_list(guess['bonusNumber'])
                guess.set('bonusNumber', eplist[0], confidence=confidence, raw=string[span[0]:span[1]])

            return guess, span

    return None, None


def process(mtree):
    SingleNodeGuesser(guess_episodes_rexps, None, log).process(mtree)

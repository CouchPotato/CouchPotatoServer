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

from guessit.transfo import SingleNodeGuesser
import re
import logging

log = logging.getLogger(__name__)


def guess_release_group(string):
    group_names = [ r'\.(Xvid)-(?P<releaseGroup>.*?)[ \.]',
                    r'\.(DivX)-(?P<releaseGroup>.*?)[\. ]',
                    r'\.(DVDivX)-(?P<releaseGroup>.*?)[\. ]',
                    ]
    for rexp in group_names:
        match = re.search(rexp, string, re.IGNORECASE)
        if match:
            metadata = match.groupdict()
            metadata.update({ 'videoCodec': match.group(1) })
            return metadata, (match.start() + 1, match.end() - 1)

    return None, None


def process(mtree):
    SingleNodeGuesser(guess_release_group, 0.8, log).process(mtree)

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
from guessit.language import search_language
from guessit.textutils import clean_string, find_words
import logging

log = logging.getLogger(__name__)


def guess_language(string):
    language, span, confidence = search_language(string)
    if language:
        return (Guess({'language': language},
                      confidence=confidence),
                span)

    return None, None


def process(mtree):
    SingleNodeGuesser(guess_language, None, log).process(mtree)
    # Note: 'language' is promoted to 'subtitleLanguage' in the post_process transfo

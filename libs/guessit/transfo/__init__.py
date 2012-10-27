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
from guessit import base_text_type, Guess
from guessit.patterns import canonical_form
from guessit.textutils import clean_string
import logging

log = logging.getLogger(__name__)


def found_property(node, name, confidence):
    node.guess = Guess({name: node.clean_value}, confidence=confidence)
    log.debug('Found with confidence %.2f: %s' % (confidence, node.guess))


def format_guess(guess):
    """Format all the found values to their natural type.
    For instance, a year would be stored as an int value, etc...

    Note that this modifies the dictionary given as input.
    """
    for prop, value in guess.items():
        if prop in ('season', 'episodeNumber', 'year', 'cdNumber',
                    'cdNumberTotal', 'bonusNumber', 'filmNumber'):
            guess[prop] = int(guess[prop])
        elif isinstance(value, base_text_type):
            if prop in ('edition',):
                value = clean_string(value)
            guess[prop] = canonical_form(value)

    return guess


def find_and_split_node(node, strategy, logger):
    string = ' %s ' % node.value # add sentinels
    for matcher, confidence in strategy:
        if getattr(matcher, 'use_node', False):
            result, span = matcher(string, node)
        else:
            result, span = matcher(string)

        if result:
            # readjust span to compensate for sentinels
            span = (span[0] - 1, span[1] - 1)

            if isinstance(result, Guess):
                if confidence is None:
                    confidence = result.confidence(list(result.keys())[0])
            else:
                if confidence is None:
                    confidence = 1.0

            guess = format_guess(Guess(result, confidence=confidence))
            msg = 'Found with confidence %.2f: %s' % (confidence, guess)
            (logger or log).debug(msg)

            node.partition(span)
            absolute_span = (span[0] + node.offset, span[1] + node.offset)
            for child in node.children:
                if child.span == absolute_span:
                    child.guess = guess
                else:
                    find_and_split_node(child, strategy, logger)
            return


class SingleNodeGuesser(object):
    def __init__(self, guess_func, confidence, logger=None):
        self.guess_func = guess_func
        self.confidence = confidence
        self.logger = logger

    def process(self, mtree):
        # strategy is a list of pairs (guesser, confidence)
        # - if the guesser returns a guessit.Guess and confidence is specified,
        #   it will override it, otherwise it will leave the guess confidence
        # - if the guesser returns a simple dict as a guess and confidence is
        #   specified, it will use it, or 1.0 otherwise
        strategy = [ (self.guess_func, self.confidence) ]

        for node in mtree.unidentified_leaves():
            find_and_split_node(node, strategy, self.logger)

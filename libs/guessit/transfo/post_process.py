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

from guessit.patterns import subtitle_exts
import logging

log = logging.getLogger(__name__)


def process(mtree):
    # 1- try to promote language to subtitle language where it makes sense
    for node in mtree.nodes():
        if 'language' not in node.guess:
            continue

        def promote_subtitle():
            # pylint: disable=W0631
            node.guess.set('subtitleLanguage', node.guess['language'],
                           confidence=node.guess.confidence('language'))
            del node.guess['language']

        # - if we matched a language in a file with a sub extension and that
        #   the group is the last group of the filename, it is probably the
        #   language of the subtitle
        #   (eg: 'xxx.english.srt')
        if (mtree.node_at((-1,)).value.lower() in subtitle_exts and
            node == mtree.leaves()[-2]):
            promote_subtitle()

        # - if a language is in an explicit group just preceded by "st",
        #   it is a subtitle language (eg: '...st[fr-eng]...')
        try:
            idx = node.node_idx
            previous = mtree.node_at((idx[0], idx[1] - 1)).leaves()[-1]
            if previous.value.lower()[-2:] == 'st':
                promote_subtitle()
        except IndexError:
            pass

    # 2- ", the" at the end of a series title should be prepended to it
    for node in mtree.nodes():
        if 'series' not in node.guess:
            continue

        series = node.guess['series']
        lseries = series.lower()

        if lseries[-4:] == ',the':
            node.guess['series'] = 'The ' + series[:-4]

        if lseries[-5:] == ', the':
            node.guess['series'] = 'The ' + series[:-5]

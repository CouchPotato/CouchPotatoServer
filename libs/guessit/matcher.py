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
from guessit import PY3, u
from guessit.matchtree import MatchTree
from guessit.guess import (merge_similar_guesses, merge_all,
                           choose_int, choose_string)
import copy
import logging

log = logging.getLogger(__name__)


class IterativeMatcher(object):
    def __init__(self, filename, filetype='autodetect'):
        """An iterative matcher tries to match different patterns that appear
        in the filename.

        The 'filetype' argument indicates which type of file you want to match.
        If it is 'autodetect', the matcher will try to see whether it can guess
        that the file corresponds to an episode, or otherwise will assume it is
        a movie.

        The recognized 'filetype' values are:
        [ autodetect, subtitle, movie, moviesubtitle, episode, episodesubtitle ]


        The IterativeMatcher works mainly in 2 steps:

        First, it splits the filename into a match_tree, which is a tree of groups
        which have a semantic meaning, such as episode number, movie title,
        etc...

        The match_tree created looks like the following:

        0000000000000000000000000000000000000000000000000000000000000000000000000000000000 111
        0000011111111111112222222222222233333333444444444444444455555555666777777778888888 000
        0000000000000000000000000000000001111112011112222333333401123334000011233340000000 000
        __________________(The.Prestige).______.[____.HP.______.{__-___}.St{__-___}.Chaps].___
        xxxxxttttttttttttt               ffffff  vvvv    xxxxxx  ll lll     xx xxx         ccc
        [XCT].Le.Prestige.(The.Prestige).DVDRip.[x264.HP.He-Aac.{Fr-Eng}.St{Fr-Eng}.Chaps].mkv

        The first 3 lines indicates the group index in which a char in the
        filename is located. So for instance, x264 is the group (0, 4, 1), and
        it corresponds to a video codec, denoted by the letter'v' in the 4th line.
        (for more info, see guess.matchtree.to_string)


         Second, it tries to merge all this information into a single object
         containing all the found properties, and does some (basic) conflict
         resolution when they arise.
        """

        valid_filetypes = ('autodetect', 'subtitle', 'video',
                           'movie', 'moviesubtitle',
                           'episode', 'episodesubtitle')
        if filetype not in valid_filetypes:
            raise ValueError("filetype needs to be one of %s" % valid_filetypes)
        if not PY3 and not isinstance(filename, unicode):
            log.warning('Given filename to matcher is not unicode...')

        self.match_tree = MatchTree(filename)
        mtree = self.match_tree
        mtree.guess.set('type', filetype, confidence=1.0)

        def apply_transfo(transfo_name, *args, **kwargs):
            transfo = __import__('guessit.transfo.' + transfo_name,
                                 globals=globals(), locals=locals(),
                                 fromlist=['process'], level=-1)
            transfo.process(mtree, *args, **kwargs)

        # 1- first split our path into dirs + basename + ext
        apply_transfo('split_path_components')

        # 2- guess the file type now (will be useful later)
        apply_transfo('guess_filetype', filetype)
        if mtree.guess['type'] == 'unknown':
            return

        # 3- split each of those into explicit groups (separated by parentheses
        #    or square brackets)
        apply_transfo('split_explicit_groups')

        # 4- try to match information for specific patterns
        # NOTE: order needs to comply to the following:
        #       - website before language (eg: tvu.org.ru vs russian)
        #       - language before episodes_rexps
        #       - properties before language (eg: he-aac vs hebrew)
        #       - release_group before properties (eg: XviD-?? vs xvid)
        if mtree.guess['type'] in ('episode', 'episodesubtitle'):
            strategy = [ 'guess_date', 'guess_website', 'guess_release_group',
                         'guess_properties', 'guess_language',
                         'guess_video_rexps',
                         'guess_episodes_rexps', 'guess_weak_episodes_rexps' ]
        else:
            strategy = [ 'guess_date', 'guess_website', 'guess_release_group',
                         'guess_properties', 'guess_language',
                         'guess_video_rexps' ]

        for name in strategy:
            apply_transfo(name)

        # more guessers for both movies and episodes
        for name in ['guess_bonus_features', 'guess_year', 'guess_country']:
            apply_transfo(name)

        # split into '-' separated subgroups (with required separator chars
        # around the dash)
        apply_transfo('split_on_dash')

        # 5- try to identify the remaining unknown groups by looking at their
        #    position relative to other known elements
        if mtree.guess['type'] in ('episode', 'episodesubtitle'):
            apply_transfo('guess_episode_info_from_position')
        else:
            apply_transfo('guess_movie_title_from_position')

        # 6- perform some post-processing steps
        apply_transfo('post_process')

        log.debug('Found match tree:\n%s' % u(mtree))

    def matched(self):
        # we need to make a copy here, as the merge functions work in place and
        # calling them on the match tree would modify it

        parts = [node.guess for node in self.match_tree.nodes() if node.guess]
        parts = copy.deepcopy(parts)

        # 1- try to merge similar information together and give it a higher
        #    confidence
        for int_part in ('year', 'season', 'episodeNumber'):
            merge_similar_guesses(parts, int_part, choose_int)

        for string_part in ('title', 'series', 'container', 'format',
                            'releaseGroup', 'website', 'audioCodec',
                            'videoCodec', 'screenSize', 'episodeFormat',
                            'audioChannels'):
            merge_similar_guesses(parts, string_part, choose_string)

        # 2- merge the rest, potentially discarding information not properly
        #    merged before
        result = merge_all(parts,
                           append=['language', 'subtitleLanguage', 'other'])

        log.debug('Final result: ' + result.nice_string())
        return result

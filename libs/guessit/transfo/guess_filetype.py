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
from guessit.patterns import (subtitle_exts, info_exts, video_exts, episode_rexps,
                              find_properties, compute_canonical_form)
from guessit.date import valid_year
from guessit.textutils import clean_string
import os.path
import re
import mimetypes
import logging

log = logging.getLogger(__name__)

# List of well known movies and series, hardcoded because they cannot be
# guessed appropriately otherwise
MOVIES = [ 'OSS 117' ]
SERIES = [ 'Band of Brothers' ]

MOVIES = [ m.lower() for m in MOVIES ]
SERIES = [ s.lower() for s in SERIES ]

def guess_filetype(mtree, filetype):
    # put the filetype inside a dummy container to be able to have the
    # following functions work correctly as closures
    # this is a workaround for python 2 which doesn't have the
    # 'nonlocal' keyword (python 3 does have it)
    filetype_container = [filetype]
    other = {}
    filename = mtree.string

    def upgrade_episode():
        if filetype_container[0] == 'video':
            filetype_container[0] = 'episode'
        elif filetype_container[0] == 'subtitle':
            filetype_container[0] = 'episodesubtitle'
        elif filetype_container[0] == 'info':
            filetype_container[0] = 'episodeinfo'

    def upgrade_movie():
        if filetype_container[0] == 'video':
            filetype_container[0] = 'movie'
        elif filetype_container[0] == 'subtitle':
            filetype_container[0] = 'moviesubtitle'
        elif filetype_container[0] == 'info':
            filetype_container[0] = 'movieinfo'

    def upgrade_subtitle():
        if 'movie' in filetype_container[0]:
            filetype_container[0] = 'moviesubtitle'
        elif 'episode' in filetype_container[0]:
            filetype_container[0] = 'episodesubtitle'
        else:
            filetype_container[0] = 'subtitle'

    def upgrade_info():
        if 'movie' in filetype_container[0]:
            filetype_container[0] = 'movieinfo'
        elif 'episode' in filetype_container[0]:
            filetype_container[0] = 'episodeinfo'
        else:
            filetype_container[0] = 'info'

    def upgrade(type='unknown'):
        if filetype_container[0] == 'autodetect':
            filetype_container[0] = type


    # look at the extension first
    fileext = os.path.splitext(filename)[1][1:].lower()
    if fileext in subtitle_exts:
        upgrade_subtitle()
        other = { 'container': fileext }
    elif fileext in info_exts:
        upgrade_info()
        other = { 'container': fileext }
    elif fileext in video_exts:
        upgrade(type='video')
        other = { 'container': fileext }
    else:
        upgrade(type='unknown')
        other = { 'extension': fileext }



    # check whether we are in a 'Movies', 'Tv Shows', ... folder
    folder_rexps = [ (r'Movies?', upgrade_movie),
                     (r'Tv[ _-]?Shows?', upgrade_episode),
                     (r'Series', upgrade_episode)
                     ]
    for frexp, upgrade_func in folder_rexps:
        frexp = re.compile(frexp, re.IGNORECASE)
        for pathgroup in mtree.children:
            if frexp.match(pathgroup.value):
                upgrade_func()

    # check for a few specific cases which will unintentionally make the
    # following heuristics confused (eg: OSS 117 will look like an episode,
    # season 1, epnum 17, when it is in fact a movie)
    fname = clean_string(filename).lower()
    for m in MOVIES:
        if m in fname:
            log.debug('Found in exception list of movies -> type = movie')
            upgrade_movie()
    for s in SERIES:
        if s in fname:
            log.debug('Found in exception list of series -> type = episode')
            upgrade_episode()

    # now look whether there are some specific hints for episode vs movie
    if filetype_container[0] in ('video', 'subtitle', 'info'):
        # if we have an episode_rexp (eg: s02e13), it is an episode
        for rexp, _, _ in episode_rexps:
            match = re.search(rexp, filename, re.IGNORECASE)
            if match:
                log.debug('Found matching regexp: "%s" (string = "%s") -> type = episode', rexp, match.group())
                upgrade_episode()
                break

        # if we have a 3-4 digit number that's not a year, maybe an episode
        match = re.search(r'[^0-9]([0-9]{3,4})[^0-9]', filename)
        if match:
            fullnumber = int(match.group()[1:-1])
            #season = fullnumber // 100
            epnumber = fullnumber % 100
            possible = True

            # check for validity
            if epnumber > 40:
                possible = False
            if valid_year(fullnumber):
                possible = False

            if possible:
                log.debug('Found possible episode number: %s (from string "%s") -> type = episode', epnumber, match.group())
                upgrade_episode()

        # if we have certain properties characteristic of episodes, it is an ep
        for prop, value, _, _ in find_properties(filename):
            log.debug('prop: %s = %s' % (prop, value))
            if prop == 'episodeFormat':
                log.debug('Found characteristic property of episodes: %s = "%s"', prop, value)
                upgrade_episode()
                break

            elif compute_canonical_form('format', value) == 'DVB':
                log.debug('Found characteristic property of episodes: %s = "%s"', prop, value)
                upgrade_episode()
                break

        # origin-specific type
        if 'tvu.org.ru' in filename:
            log.debug('Found characteristic property of episodes: %s = "%s"', prop, value)
            upgrade_episode()

        # if no episode info found, assume it's a movie
        log.debug('Nothing characteristic found, assuming type = movie')
        upgrade_movie()

    filetype = filetype_container[0]
    return filetype, other


def process(mtree, filetype='autodetect'):
    filetype, other = guess_filetype(mtree, filetype)

    mtree.guess.set('type', filetype, confidence=1.0)
    log.debug('Found with confidence %.2f: %s' % (1.0, mtree.guess))

    filetype_info = Guess(other, confidence=1.0)
    # guess the mimetype of the filename
    # TODO: handle other mimetypes not found on the default type_maps
    # mimetypes.types_map['.srt']='text/subtitle'
    mime, _ = mimetypes.guess_type(mtree.string, strict=False)
    if mime is not None:
        filetype_info.update({'mimetype': mime}, confidence=1.0)

    node_ext = mtree.node_at((-1,))
    node_ext.guess = filetype_info
    log.debug('Found with confidence %.2f: %s' % (1.0, node_ext.guess))

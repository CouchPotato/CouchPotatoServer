#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2011 Nicolas Wack <wackou@gmail.com>
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

#from guessit import movie, episode
import os, os.path
import logging

log = logging.getLogger('guessit.autodetect')

def within(x, nrange):
    """Return whether a number is inside a given range, specified as a list or tuple
    of the lower and upper bounds."""
    low, high = nrange
    return low <= x <= high

def guess_filename_info(filename):
    log.debug('Trying to guess info for file: ' + filename)

    # try to guess info as if it were an episode
    episode_info = episode.guess_episode_filename(filename)

    # 1- if we found either season/episodeNumber, then we're pretty sure it must
    #    be an episode
    if 'season' in episode_info or 'episodeNumber' in episode_info:
        log.debug('Likely an episode as it contains season and/or episodeNumber: ' + filename)
        episode_info.update({ 'type': 'episode' }, confidence = 0.9)
        return episode_info

    # try to guess info as if it were a movie
    movie_info = movie.guess_movie_filename(filename)

    # 2- if the file exists, try to guess its type using its size
    if os.path.exists(filename):
        size = os.stat(filename).st_size / (1024 * 1024)

        # if size <=  1/2 of 1CD -> episode (very unlikely a movie so small)
        if size < 400:
            log.debug('Likely an episode due to its small size (%dMB): %s' % (size, filename))
            episode_info.update({ 'type': 'episode' }, confidence = 0.8)
            return episode_info

        # if size > 2G -> movie (even fullHD eps aren't that big yet)
        if size > 2048:
            log.debug('Likely a movie due to its big size (%dMB): %s' % (size, filename))
            movie_info.update({ 'type': 'movie' }, confidence = 0.8)
            return movie_info

        # if size == 1CD or 2CDs -> movie
        if within(size, [690, 710]) or within(size, [1380, 1420]):
            log.debug('Likely a movie due to its size close to a CD size (%dMB): %s' % (size, filename))
            movie_info.update({ 'type': 'movie' }, confidence = 0.8)
            return movie_info


    # 3- if all else fails, assume it's a movie
    log.debug('Couldn\'t make an informed guess... Assuming file is a movie: %s' % filename)
    movie_info.update({ 'type': 'movie' }, confidence = 0.5)
    return movie_info

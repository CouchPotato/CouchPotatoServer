# -*- coding: utf-8 -*-
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
from . import subtitles
from .languages import list_languages
import enzyme
import guessit
import hashlib
import logging
import mimetypes
import os
import struct


__all__ = ['EXTENSIONS', 'MIMETYPES', 'Video', 'Episode', 'Movie', 'UnknownVideo',
           'scan', 'hash_opensubtitles', 'hash_thesubdb']
logger = logging.getLogger(__name__)

#: Video extensions
EXTENSIONS = ['.avi', '.mkv', '.mpg', '.mp4', '.m4v', '.mov', '.ogm', '.ogv', '.wmv',
              '.divx', '.asf']

#: Video mimetypes
MIMETYPES = ['video/mpeg', 'video/mp4', 'video/quicktime', 'video/x-ms-wmv', 'video/x-msvideo',
             'video/x-flv', 'video/x-matroska', 'video/x-matroska-3d']


class Video(object):
    """Base class for videos

    :param string path: path
    :param guess: guessed informations
    :type guess: :class:`~guessit.guess.Guess`
    :param string imdbid: imdbid

    """
    def __init__(self, path, guess, imdbid=None):
        self.release = path
        self.guess = guess
        self.imdbid = imdbid
        self._path = None
        self.hashes = {}
        if os.path.exists(path):
            self._path = path
            self.size = os.path.getsize(self._path)
            self._compute_hashes()

    @classmethod
    def from_path(cls, path):
        """Create a :class:`Video` subclass guessing all informations from the given path

        :param string path: path
        :return: video object
        :rtype: :class:`Episode` or :class:`Movie` or :class:`UnknownVideo`

        """
        guess = guessit.guess_file_info(path, 'autodetect')
        result = None
        if guess['type'] == 'episode' and 'series' in guess and 'season' in guess and 'episodeNumber' in guess:
            title = None
            if 'title' in guess:
                title = guess['title']
            result = Episode(path, guess['series'], guess['season'], guess['episodeNumber'], title, guess)
        if guess['type'] == 'movie' and 'title' in guess:
            year = None
            if 'year' in guess:
                year = guess['year']
            result = Movie(path, guess['title'], year, guess)
        if not result:
            result = UnknownVideo(path, guess)
        if not isinstance(result, cls):
            raise ValueError('Video is not of requested type')
        return result

    @property
    def exists(self):
        """Whether the video exists or not"""
        if self._path:
            return os.path.exists(self._path)
        return False

    @property
    def path(self):
        """Path to the video"""
        return self._path

    @path.setter
    def path(self, value):
        if not os.path.exists(value):
            raise ValueError('Path does not exists')
        self._path = value
        self.size = os.path.getsize(self._path)
        self._compute_hashes()

    def _compute_hashes(self):
        """Compute different hashes"""
        self.hashes['OpenSubtitles'] = hash_opensubtitles(self.path)
        self.hashes['TheSubDB'] = hash_thesubdb(self.path)

    def scan(self):
        """Scan and return associated subtitles

        :return: associated subtitles
        :rtype: list of :class:`~subliminal.subtitles.Subtitle`

        """
        if not self.exists:
            return []
        basepath = os.path.splitext(self.path)[0]
        results = []
        video_infos = None
        try:
            video_infos = enzyme.parse(self.path)
            logger.debug(u'Succeeded parsing %s with enzyme: %r' % (self.path, video_infos))
        except:
            logger.debug(u'Failed parsing %s with enzyme' % self.path)
        if isinstance(video_infos, enzyme.core.AVContainer):
            results.extend([subtitles.EmbeddedSubtitle.from_enzyme(self.path, s) for s in video_infos.subtitles])
        for l in list_languages(1):
            for e in subtitles.EXTENSIONS:
                single_path = basepath + '%s' % e
                if os.path.exists(single_path):
                    results.append(subtitles.ExternalSubtitle(single_path, None))
                multi_path = basepath + '.%s%s' % (l, e)
                if os.path.exists(multi_path):
                    results.append(subtitles.ExternalSubtitle(multi_path, l))
        return results

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.release)


class Episode(Video):
    """Episode :class:`Video`

    :param string path: path
    :param string series: series
    :param int season: season number
    :param int episode: episode number
    :param string title: title
    :param guess: guessed informations
    :type guess: :class:`~guessit.guess.Guess`
    :param string tvdbid: tvdbid
    :param string imdbid: imdbid

    """
    def __init__(self, path, series, season, episode, title=None, guess=None, tvdbid=None, imdbid=None):
        super(Episode, self).__init__(path, guess, imdbid)
        self.series = series
        self.title = title
        self.season = season
        self.episode = episode
        self.tvdbid = tvdbid


class Movie(Video):
    """Movie :class:`Video`

    :param string path: path
    :param string title: title
    :param int year: year
    :param guess: guessed informations
    :type guess: :class:`~guessit.guess.Guess`
    :param string imdbid: imdbid

    """
    def __init__(self, path, title, year=None, guess=None, imdbid=None):
        super(Movie, self).__init__(path, guess, imdbid)
        self.title = title
        self.year = year


class UnknownVideo(Video):
    """Unknown video"""
    pass


def scan(entry, max_depth=3, depth=0):
    """Scan a path for videos and subtitles

    :param string entry: path
    :param int max_depth: maximum folder depth
    :param int depth: starting depth
    :return: found videos and subtitles
    :rtype: list of (:class:`Video`, [:class:`~subliminal.subtitles.Subtitle`])

    """
    if depth > max_depth and max_depth != 0:  # we do not want to search the whole file system except if max_depth = 0
        return []
    if depth == 0:
        entry = os.path.abspath(entry)
    if os.path.isdir(entry):  # a dir? recurse
        logger.debug(u'Scanning directory %s with depth %d/%d' % (entry, depth, max_depth))
        result = []
        for e in os.listdir(entry):
            result.extend(scan(os.path.join(entry, e), max_depth, depth + 1))
        return result
    if os.path.isfile(entry) or depth == 0:
        logger.debug(u'Scanning file %s with depth %d/%d' % (entry, depth, max_depth))
        if depth != 0:  # trust the user: only check for valid format if recursing
            if mimetypes.guess_type(entry)[0] not in MIMETYPES and os.path.splitext(entry)[1] not in EXTENSIONS:
                return []
        video = Video.from_path(entry)
        return [(video, video.scan())]
    logger.warning(u'Scanning entry %s failed with depth %d/%d' % (entry, depth, max_depth))
    return []  # anything else


def hash_opensubtitles(path):
    """Compute a hash using OpenSubtitles' algorithm

    :param string path: path
    :return: hash
    :rtype: string

    """
    longlongformat = 'q'  # long long
    bytesize = struct.calcsize(longlongformat)
    with open(path, 'rb') as f:
        filesize = os.path.getsize(path)
        filehash = filesize
        if filesize < 65536 * 2:
            return None
        for _ in range(65536 / bytesize):
            filebuffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, filebuffer)
            filehash += l_value
            filehash = filehash & 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number
        f.seek(max(0, filesize - 65536), 0)
        for _ in range(65536 / bytesize):
            filebuffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, filebuffer)
            filehash += l_value
            filehash = filehash & 0xFFFFFFFFFFFFFFFF
    returnedhash = '%016x' % filehash
    logger.debug(u'Computed OpenSubtitle hash %s for %s' % (returnedhash, path))
    return returnedhash


def hash_thesubdb(path):
    """Compute a hash using TheSubDB's algorithm

    :param string path: path
    :return: hash
    :rtype: string

    """
    readsize = 64 * 1024
    with open(path, 'rb') as f:
        data = f.read(readsize)
        f.seek(-readsize, os.SEEK_END)
        data += f.read(readsize)
    returnedhash = hashlib.md5(data).hexdigest()
    logger.debug(u'Computed TheSubDB hash %s for %s' % (returnedhash, path))
    return returnedhash

# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
# Copyright (c) 2011 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of Subliminal.
#
# Subliminal is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__all__ = ['EXTENSIONS', 'MIMETYPES', 'Video', 'Episode', 'Movie', 'UnknownVideo', 'scan']


from languages import list_languages
import abc
import enzyme
import guessit
import hashlib
import mimetypes
import os
import struct
import subprocess
import subtitles


EXTENSIONS = ['.avi', '.mkv', '.mpg', '.mp4', '.m4v', '.mov', '.ogm', '.ogv', '.wmv', '.divx', '.asf']
MIMETYPES = ['video/mpeg', 'video/mp4', 'video/quicktime', 'video/x-ms-wmv', 'video/x-msvideo', 'video/x-flv', 'video/x-matroska', 'video/x-matroska-3d']


class Video(object):
    __metaclass__ = abc.ABCMeta
    """Base class for videos"""
    def __init__(self, release, guess, imdbid=None):
        self.release = release
        self.guess = guess
        self.imdbid = imdbid
        self._path = None
        self.hashes = {}
        if os.path.exists(release):
            self.path = release

    @classmethod
    def fromPath(cls, path):
        """Create a Video object guessing all informations from the given release/path"""
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
        if self._path:
            return os.path.exists(self._path)
        return False

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        if not os.path.exists(value):
            raise ValueError('Path does not exists')
        self._path = value
        self.size = os.path.getsize(self._path)
        self._computeHashes()

    def _computeHashes(self):
        self.hashes['OpenSubtitles'] = self._computeHashOpenSubtitles()
        self.hashes['TheSubDB'] = self._computeHashTheSubDB()

    def _computeHashOpenSubtitles(self):
        """Hash a file like OpenSubtitles"""
        longlongformat = 'q'  # long long
        bytesize = struct.calcsize(longlongformat)
        f = open(self.path, 'rb')
        filesize = os.path.getsize(self.path)
        filehash = filesize
        if filesize < 65536 * 2:
            return []
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
        f.close()
        returnedhash = '%016x' % filehash
        return returnedhash

    def _computeHashTheSubDB(self):
        """Hash a file like TheSubDB"""
        readsize = 64 * 1024
        with open(self.path, 'rb') as f:
            data = f.read(readsize)
            f.seek(-readsize, os.SEEK_END)
            data += f.read(readsize)
        return hashlib.md5(data).hexdigest()

    def mkvmerge(self, subs, out=None, mkvmerge_bin='mkvmerge', title=None):
        """Merge the video with subs"""
        if not out:
            out = self.path + '.merged.mkv'
        args = [mkvmerge_bin, '-o', out, self.path]
        if title:
            args += ['--title', title]
        for sub in subs:
            if sub.language:
                track_id = 0
                if isinstance(sub, subtitles.EmbeddedSubtitle):
                    track_id = sub.track_id
                args += ['--language', str(track_id) + ':' + sub.language, sub.path]
            continue
            args += [sub.path]
        with open(os.devnull, 'w') as devnull:
            p = subprocess.Popen(args, stdout=devnull, stderr=devnull)
        p.wait()

    def scan(self):
        """Scan and return associated Subtitles"""
        if not self.exists:
            return []
        basepath = os.path.splitext(self.path)[0]
        results = []
        video_infos = None
        try:
            video_infos = enzyme.parse(self.path)
        except enzyme.ParseError:
            pass
        if isinstance(video_infos, enzyme.core.AVContainer):
            results.extend([subtitles.EmbeddedSubtitle.fromEnzyme(self.path, s) for s in video_infos.subtitles])
        for l in list_languages(1):
            for e in subtitles.EXTENSIONS:
                single_path = basepath + '%s' % e
                if os.path.exists(single_path):
                    results.append(subtitles.ExternalSubtitle(single_path, None))
                multi_path = basepath + '.%s%s' % (l, e)
                if os.path.exists(multi_path):
                    results.append(subtitles.ExternalSubtitle(multi_path, l))
        return results


class Episode(Video):
    """Episode class"""
    def __init__(self, release, series, season, episode, title=None, guess=None, tvdbid=None, imdbid=None):
        super(Episode, self).__init__(release, guess, imdbid)
        self.series = series
        self.title = title
        self.season = season
        self.episode = episode
        self.tvdbid = tvdbid


class Movie(Video):
    """Movie class"""
    def __init__(self, release, title, year=None, guess=None, imdbid=None):
        super(Movie, self).__init__(release, guess, imdbid)
        self.title = title
        self.year = year


class UnknownVideo(Video):
    """Unknown video"""
    def __init__(self, release, guess, imdbid=None):
        super(UnknownVideo, self).__init__(release, guess, imdbid)
        self.guess = guess


def scan(entry, max_depth=3, depth=0):
    """Scan a path and return a list of tuples (video, [subtitle])"""
    if depth > max_depth and max_depth != 0:  # we do not want to search the whole file system except if max_depth = 0
        return []
    if depth == 0:
        entry = os.path.abspath(entry)
    if os.path.isfile(entry):  # a file? scan it
        if depth != 0:  # trust the user: only check for valid format if recursing
            if mimetypes.guess_type(entry)[0] not in MIMETYPES and os.path.splitext(entry)[1] not in EXTENSIONS:
                return []
        video = Video.fromPath(entry)
        return [(video, video.scan())]
    if os.path.isdir(entry):  # a dir? recurse
        result = []
        for e in os.listdir(entry):
            result.extend(scan(os.path.join(entry, e), max_depth, depth + 1))
        return result
    return []  # anything else

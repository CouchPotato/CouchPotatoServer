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
from .languages import list_languages, convert_language
import os.path


__all__ = ['Subtitle', 'EmbeddedSubtitle', 'ExternalSubtitle', 'ResultSubtitle', 'get_subtitle_path']


#: Subtitles extensions
EXTENSIONS = ['.srt', '.sub', '.txt']


class Subtitle(object):
    """Base class for subtitles

    :param string path: path to the subtitle
    :param string language: language of the subtitle (second element of :class:`~subliminal.languages.LANGUAGES`)

    """
    def __init__(self, path, language):
        self.path = path
        self.language = language

    @property
    def exists(self):
        """Whether the subtitle exists or not"""
        if self.path:
            return os.path.exists(self.path)
        return False


class EmbeddedSubtitle(Subtitle):
    """Subtitle embedded in a container

    :param string path: path to the subtitle
    :param string language: language of the subtitle (second element of :class:`~subliminal.languages.LANGUAGES`)
    :param int track_id: id of the subtitle track in the container

    """
    def __init__(self, path, language, track_id):
        super(EmbeddedSubtitle, self).__init__(path, language)
        self.track_id = track_id

    @classmethod
    def from_enzyme(cls, path, subtitle):
        language = convert_language(subtitle.language, 1, 2)
        return cls(path, language, subtitle.trackno)


class ExternalSubtitle(Subtitle):
    """Subtitle in a file next to the video file"""
    @classmethod
    def from_path(cls, path):
        """Create an :class:`ExternalSubtitle` from path"""
        extension = ''
        for e in EXTENSIONS:
            if path.endswith(e):
                extension = e
                break
        if not extension:
            raise ValueError('Not a supported subtitle extension')
        language = os.path.splitext(path[:len(path) - len(extension)])[1][1:]
        if not language in list_languages(1):
            language = None
        return cls(path, language)


class ResultSubtitle(ExternalSubtitle):
    """Subtitle found using :mod:`~subliminal.services`

    :param string path: path to the subtitle
    :param string language: language of the subtitle (second element of :class:`~subliminal.languages.LANGUAGES`)
    :param string service: name of the service
    :param string link: download link for the subtitle
    :param string release: release name of the video
    :param float confidence: confidence that the subtitle matches the video according to the service
    :param set keywords: keywords that describe the subtitle

    """
    def __init__(self, path, language, service, link, release=None, confidence=1, keywords=set()):
        super(ResultSubtitle, self).__init__(path, language)
        self.service = service
        self.link = link
        self.release = release
        self.confidence = confidence
        self.keywords = keywords

    @property
    def single(self):
        """Whether this is a single subtitle or not. A single subtitle does not have
        a language indicator in its file name

        :rtype: bool

        """
        extension = os.path.splitext(self.path)[0]
        language = os.path.splitext(self.path[:len(self.path) - len(extension)])[1][1:]
        if not language in list_languages(1):
            return True
        return False

    def __repr__(self):
        return 'ResultSubtitle(%s, %s, %.2f, %s)' % (self.language, self.service, self.confidence, self.release)


def get_subtitle_path(video_path, language, multi):
    """Create the subtitle path from the given video path using language if multi"""
    if not os.path.exists(video_path):
        path = os.path.splitext(os.path.basename(video_path))[0]
    else:
        path = os.path.splitext(video_path)[0]
    if multi and language:
        return path + '.%s%s' % (language, EXTENSIONS[0])
    return path + '%s' % EXTENSIONS[0]

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
from .language import Language
from .utils import to_unicode
import os.path


__all__ = ['Subtitle', 'EmbeddedSubtitle', 'ExternalSubtitle', 'ResultSubtitle', 'get_subtitle_path']

#: Subtitles extensions
EXTENSIONS = ['.srt', '.sub', '.txt']


class Subtitle(object):
    """Base class for subtitles

    :param string path: path to the subtitle
    :param language: language of the subtitle
    :type language: :class:`~subliminal.language.Language`

    """
    def __init__(self, path, language):
        if not isinstance(language, Language):
            raise TypeError('%r is not an instance of Language')
        self.path = path
        self.language = language

    @property
    def exists(self):
        """Whether the subtitle exists or not"""
        if self.path:
            return os.path.exists(self.path)
        return False

    def __unicode__(self):
        return to_unicode(self.path)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __repr__(self):
        return '%s(%s, %s)' % (self.__class__.__name__, self, self.language)


class EmbeddedSubtitle(Subtitle):
    """Subtitle embedded in a container

    :param string path: path to the subtitle
    :param language: language of the subtitle
    :type language: :class:`~subliminal.language.Language`
    :param int track_id: id of the subtitle track in the container

    """
    def __init__(self, path, language, track_id):
        super(EmbeddedSubtitle, self).__init__(path, language)
        self.track_id = track_id

    @classmethod
    def from_enzyme(cls, path, subtitle):
        language = Language(subtitle.language, strict=False)
        return cls(path, language, subtitle.trackno)


class ExternalSubtitle(Subtitle):
    """Subtitle in a file next to the video file"""
    @classmethod
    def from_path(cls, path):
        """Create an :class:`ExternalSubtitle` from path"""
        extension = None
        for e in EXTENSIONS:
            if path.endswith(e):
                extension = e
                break
        if extension is None:
            raise ValueError('Not a supported subtitle extension')
        language = Language(os.path.splitext(path[:len(path) - len(extension)])[1][1:], strict=False)
        return cls(path, language)


class ResultSubtitle(ExternalSubtitle):
    """Subtitle found using :mod:`~subliminal.services`

    :param string path: path to the subtitle
    :param language: language of the subtitle
    :type language: :class:`~subliminal.language.Language`
    :param string service: name of the service
    :param string link: download link for the subtitle
    :param string release: release name of the video
    :param float confidence: confidence that the subtitle matches the video according to the service
    :param set keywords: keywords that describe the subtitle

    """
    def __init__(self, path, language, service, link, release=None, confidence=1, keywords=None):
        super(ResultSubtitle, self).__init__(path, language)
        self.service = service
        self.link = link
        self.release = release
        self.confidence = confidence
        self.keywords = keywords or set()

    @property
    def single(self):
        """Whether this is a single subtitle or not. A single subtitle does not have
        a language indicator in its file name

        :rtype: bool

        """
        return self.language == Language('Undetermined')

    def __repr__(self):
        if not self.release:
            return 'ResultSubtitle(%s, %s, %s, %.2f)' % (self.path, self.language, self.service, self.confidence)
        return 'ResultSubtitle(%s, %s, %s, %.2f, release=%s)' % (self.path, self.language, self.service, self.confidence, self.release.encode('ascii', 'ignore'))


def get_subtitle_path(video_path, language, multi):
    """Create the subtitle path from the given video path using language if multi

    :param string video_path: path to the video
    :param language: language of the subtitle
    :type language: :class:`~subliminal.language.Language`
    :param bool multi: whether to use multi language naming or not
    :return: path of the subtitle
    :rtype: string

    """
    if not os.path.exists(video_path):
        path = os.path.splitext(os.path.basename(video_path))[0]
    else:
        path = os.path.splitext(video_path)[0]
    if multi and language:
        return path + '.%s%s' % (language.alpha2, EXTENSIONS[0])
    return path + '%s' % EXTENSIONS[0]

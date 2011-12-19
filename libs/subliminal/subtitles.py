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
__all__ = ['Subtitle', 'EmbeddedSubtitle', 'ExternalSubtitle', 'ResultSubtitle', 'get_subtitle_path']


from subliminal.languages import list_languages, convert_language
import abc
import os.path


EXTENSIONS = ['.srt', '.sub', '.txt']


class Subtitle(object):
    __metaclass__ = abc.ABCMeta
    """Base class for subtitles"""

    def __init__(self, path, language):
        self.path = path
        self.language = language

    @property
    def exists(self):
        if self.path:
            return os.path.exists(self.path)
        return False

    @classmethod
    def fromPath(cls, path):
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


class EmbeddedSubtitle(Subtitle):
    def __init__(self, path, language, track_id):
        super(EmbeddedSubtitle, self).__init__(path, language)
        self.track_id = track_id

    @classmethod
    def fromEnzyme(cls, path, subtitle):
        language = convert_language(subtitle.language, 1, 2)
        return cls(path, language, subtitle.trackno)


class ExternalSubtitle(Subtitle):
    pass


class ResultSubtitle(ExternalSubtitle):
    def __init__(self, path, language, plugin, link, release=None, confidence=1, keywords=set()):
        super(ResultSubtitle, self).__init__(path, language)
        self.plugin = plugin
        self.link = link
        self.release = release
        self.confidence = confidence
        self.keywords = keywords

    @property
    def single(self):
        extension = os.path.splitext(self.path)[0]
        language = os.path.splitext(self.path[:len(self.path) - len(extension)])[1][1:]
        if not language in list_languages(1):
            return True
        return False

    def convert(self):
        converted = {'path': self.path, 'plugin': self.plugin, 'language': self.language, 'link': self.link, 'release': self.release,
                     'confidence': self.confidence, 'keywords': self.keywords}
        return converted

    def __str__(self):
        return repr(self.convert())


def get_subtitle_path(video_path, language, multi):
    """Create the subtitle path from the given video path using language if multi"""
    if not os.path.exists(video_path):
        path = os.path.splitext(os.path.basename(video_path))[0]
    else:
        path = os.path.splitext(video_path)[0]
    if multi and language:
        return path + '.%s%s' % (language, EXTENSIONS[0])
    return path + '%s' % EXTENSIONS[0]

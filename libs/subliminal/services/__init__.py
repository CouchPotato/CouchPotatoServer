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
from ..cache import Cache
from ..exceptions import DownloadFailedError, ServiceError
from ..language import language_set, Language
from ..subtitles import EXTENSIONS
import logging
import os
import requests
import threading
import zipfile


__all__ = ['ServiceBase', 'ServiceConfig']
logger = logging.getLogger(__name__)


class ServiceBase(object):
    """Service base class

    :param config: service configuration
    :type config: :class:`ServiceConfig`

    """
    #: URL to the service server
    server_url = ''

    #: User Agent for any HTTP-based requests
    user_agent = 'subliminal v0.6'

    #: Whether based on an API or not
    api_based = False

    #: Timeout for web requests
    timeout = 5

    #: :class:`~subliminal.language.language_set` of available languages
    languages = language_set()

    #: Map between language objects and language codes used in the service
    language_map = {}

    #: Default attribute of a :class:`~subliminal.language.Language` to get with :meth:`get_code`
    language_code = 'alpha2'

    #: Accepted video classes (:class:`~subliminal.videos.Episode`, :class:`~subliminal.videos.Movie`, :class:`~subliminal.videos.UnknownVideo`)
    videos = []

    #: Whether the video has to exist or not
    require_video = False

    #: List of required features for BeautifulSoup
    required_features = None

    def __init__(self, config=None):
        self.config = config or ServiceConfig()
        self.session = None

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, *args):
        self.terminate()

    def init(self):
        """Initialize connection"""
        logger.debug(u'Initializing %s' % self.__class__.__name__)
        self.session = requests.session(timeout=10, headers={'User-Agent': self.user_agent})

    def init_cache(self):
        """Initialize cache, make sure it is loaded from disk"""
        if not self.config or not self.config.cache:
            raise ServiceError('Cache directory is required')
        self.config.cache.load(self.__class__.__name__)

    def save_cache(self):
        self.config.cache.save(self.__class__.__name__)

    def clear_cache(self):
        self.config.cache.clear(self.__class__.__name__)

    def cache_for(self, func, args, result):
        return self.config.cache.cache_for(self.__class__.__name__, func, args, result)

    def cached_value(self, func, args):
        return self.config.cache.cached_value(self.__class__.__name__, func, args)

    def terminate(self):
        """Terminate connection"""
        logger.debug(u'Terminating %s' % self.__class__.__name__)

    def get_code(self, language):
        """Get the service code for a :class:`~subliminal.language.Language`

        It uses the :data:`language_map` and if there's no match, falls back
        on the :data:`language_code` attribute of the given :class:`~subliminal.language.Language`

        """
        if language in self.language_map:
            return self.language_map[language]
        if self.language_code is None:
            raise ValueError('%r has no matching code' % language)
        return getattr(language, self.language_code)

    def get_language(self, code):
        """Get a :class:`~subliminal.language.Language` from a service code

        It uses the :data:`language_map` and if there's no match, uses the
        given code as ``language`` parameter for the :class:`~subliminal.language.Language`
        constructor

        .. note::

            A warning is emitted if the generated :class:`~subliminal.language.Language`
            is "Undetermined"

        """
        if code in self.language_map:
            return self.language_map[code]
        language = Language(code, strict=False)
        if language == Language('Undetermined'):
            logger.warning(u'Code %s could not be identified as a language for %s' % (code, self.__class__.__name__))
        return language

    def query(self, *args):
        """Make the actual query"""
        raise NotImplementedError()

    def list(self, video, languages):
        """List subtitles

        As a service writer, you can either override this method or implement
        :meth:`list_checked` instead to have the languages pre-filtered for you

        """
        if not self.check_validity(video, languages):
            return []
        return self.list_checked(video, languages)

    def list_checked(self, video, languages):
        """List subtitles without having to check parameters for validity"""
        raise NotImplementedError()

    def download(self, subtitle):
        """Download a subtitle"""
        self.download_file(subtitle.link, subtitle.path)
        return subtitle

    @classmethod
    def check_validity(cls, video, languages):
        """Check for video and languages validity in the Service

        :param video: the video to check
        :type video: :class:`~subliminal.videos.video`
        :param languages: languages to check
        :type languages: :class:`~subliminal.language.Language`
        :rtype: bool

        """
        languages = (languages & cls.languages) - language_set(['Undetermined'])
        if not languages:
            logger.debug(u'No language available for service %s' % cls.__name__.lower())
            return False
        if cls.require_video and not video.exists or not isinstance(video, tuple(cls.videos)):
            logger.debug(u'%r is not valid for service %s' % (video, cls.__name__.lower()))
            return False
        return True

    def download_file(self, url, filepath):
        """Attempt to download a file and remove it in case of failure

        :param string url: URL to download
        :param string filepath: destination path

        """
        logger.info(u'Downloading %s in %s' % (url, filepath))
        try:
            r = self.session.get(url, headers={'Referer': url, 'User-Agent': self.user_agent})
            with open(filepath, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            logger.error(u'Download failed: %s' % e)
            if os.path.exists(filepath):
                os.remove(filepath)
            raise DownloadFailedError(str(e))
        logger.debug(u'Download finished')

    def download_zip_file(self, url, filepath):
        """Attempt to download a zip file and extract any subtitle file from it, if any.
        This cleans up after itself if anything fails.

        :param string url: URL of the zip file to download
        :param string filepath: destination path for the subtitle

        """
        logger.info(u'Downloading %s in %s' % (url, filepath))
        try:
            zippath = filepath + '.zip'
            r = self.session.get(url, headers={'Referer': url, 'User-Agent': self.user_agent})
            with open(zippath, 'wb') as f:
                f.write(r.content)
            if not zipfile.is_zipfile(zippath):
                # TODO: could check if maybe we already have a text file and
                # download it directly
                raise DownloadFailedError('Downloaded file is not a zip file')
            with zipfile.ZipFile(zippath) as zipsub:
                for subfile in zipsub.namelist():
                    if os.path.splitext(subfile)[1] in EXTENSIONS:
                        with open(filepath, 'w') as f:
                            f.write(zipsub.open(subfile).read())
                        break
                else:
                    raise DownloadFailedError('No subtitles found in zip file')
            os.remove(zippath)
        except Exception as e:
            logger.error(u'Download %s failed: %s' % (url, e))
            if os.path.exists(zippath):
                os.remove(zippath)
            if os.path.exists(filepath):
                os.remove(filepath)
            raise DownloadFailedError(str(e))
        logger.debug(u'Download finished')


class ServiceConfig(object):
    """Configuration for any :class:`Service`

    :param bool multi: whether to download one subtitle per language or not
    :param string cache_dir: cache directory

    """
    def __init__(self, multi=False, cache_dir=None):
        self.multi = multi
        self.cache_dir = cache_dir
        self.cache = None
        if cache_dir is not None:
            self.cache = Cache(cache_dir)

    def __repr__(self):
        return 'ServiceConfig(%r, %s)' % (self.multi, self.cache.cache_dir)

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
from .. import cache
from ..exceptions import MissingLanguageError, DownloadFailedError, ServiceError
from ..subtitles import EXTENSIONS
from guessit.language import lang_set, UNDETERMINED
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

    #: Mapping to Service's language codes and subliminal's
    languages = {}

    #: Accepted video classes (:class:`~subliminal.videos.Episode`, :class:`~subliminal.videos.Movie`, :class:`~subliminal.videos.UnknownVideo`)
    videos = []

    #: Whether the video has to exist or not
    require_video = False

    #: List of required features for BeautifulSoup
    required_features = None

    def __init__(self, config=None):
        self.config = config or ServiceConfig()

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

        service_name = self.__class__.__name__
        self.config.cache.load(service_name)

    def save_cache(self):
        service_name = self.__class__.__name__
        self.config.cache.save(service_name)

    def clear_cache(self):
        service_name = self.__class__.__name__
        self.config.cache.clear(service_name)

    def cache_for(self, func, args, result):
        service_name = self.__class__.__name__
        return self.config.cache.cache_for(service_name, func, args, result)

    def cached_value(self, func, args):
        service_name = self.__class__.__name__
        return self.config.cache.cached_value(service_name, func, args)

    def terminate(self):
        """Terminate connection"""
        logger.debug(u'Terminating %s' % self.__class__.__name__)

    def query(self, *args):
        """Make the actual query"""
        pass

    def list(self, video, languages):
        """List subtitles

        As a service writer, you can either override this method or implement
        :meth:`list_checked` instead to have the languages pre-filtered for you

        """
        if not self.check_validity(video, languages):
            return []
        return self.list_checked(video, languages)

    def download(self, subtitle):
        """Download a subtitle"""
        self.download_file(subtitle.link, subtitle.path)

    @classmethod
    def check_validity(cls, video, languages):
        """Check for video and languages validity in the Service

        :param video: the video to check
        :type video: :class:`~subliminal.videos.video`
        :param set languages: languages to check
        :rtype: bool

        """
        languages = (lang_set(languages) & cls.languages) - set([UNDETERMINED])
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
        logger.info(u'Downloading %s' % url)
        try:
            r = self.session.get(url, headers={'Referer': url, 'User-Agent': self.user_agent})
            with open(filepath, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            logger.error(u'Download %s failed: %s' % (url, e))
            if os.path.exists(filepath):
                os.remove(filepath)
            raise DownloadFailedError(str(e))
        logger.debug(u'Download finished for file %s. Size: %s' % (filepath, os.path.getsize(filepath)))

    def download_zip_file(self, url, filepath):
        """Attempt to download a zip file and extract any subtitle file from it, if any.
        This cleans up after itself if anything fails.

        :param string url: URL of the zip file to download
        :param string filepath: destination path for the subtitle

        """
        logger.info(u'Downloading %s' % url)
        try:
            zippath = filepath + '.zip'
            r = self.session.get(url, headers={'Referer': url, 'User-Agent': self.user_agent})
            with open(zippath, 'wb') as f:
                f.write(r.content)
            if not zipfile.is_zipfile(zippath):
                # TODO: could check if maybe we already have a text file and
                # download it directly
                raise DownloadFailedError('Downloaded file is not a zip file')
            zipsub = zipfile.ZipFile(zippath)
            for subfile in zipsub.namelist():
                if os.path.splitext(subfile)[1] in EXTENSIONS:
                    open(filepath, 'w').write(zipsub.open(subfile).read())
                    break
            else:
                logger.debug(u'No subtitles found in zip file')
                raise DownloadFailedError('No subtitles found in zip file')
            os.remove(zippath)
            logger.debug(u'Download finished for file %s. Size: %s' % (filepath, os.path.getsize(filepath)))
            return
        except Exception as e:
            logger.error(u'Download %s failed: %s' % (url, e))
            if os.path.exists(zippath):
                os.remove(zippath)
            if os.path.exists(filepath):
                os.remove(filepath)
            raise DownloadFailedError(str(e))


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
            self.cache = cache.Cache(cache_dir)

    def __repr__(self):
        return 'ServiceConfig(%r, %s)' % (self.multi, self.cache.cache_dir)

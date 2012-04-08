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
from . import ServiceBase
from ..exceptions import ServiceError
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..videos import Episode
from ..utils import to_unicode
import BeautifulSoup
import logging
import os.path
import urllib
try:
    import cPickle as pickle
except ImportError:
    import pickle


logger = logging.getLogger(__name__)


class BierDopje(ServiceBase):
    server_url = 'http://api.bierdopje.com/A2B638AC5D804C2E/'
    api_based = True
    languages = {'en': 'en', 'nl': 'nl'}
    reverted_languages = False
    videos = [Episode]
    require_video = False

    def __init__(self, config=None):
        super(BierDopje, self).__init__(config)
        self.showids = {}
        if self.config and self.config.cache_dir:
            self.init_cache()

    def init_cache(self):
        logger.debug(u'Initializing cache...')
        if not self.config or not self.config.cache_dir:
            raise ServiceError('Cache directory is required')
        self.showids_cache = os.path.join(self.config.cache_dir, 'bierdopje_showids.cache')
        if not os.path.exists(self.showids_cache):
            self.save_cache()

    def save_cache(self):
        logger.debug(u'Saving showids to cache...')
        with self.lock:
            with open(self.showids_cache, 'w') as f:
                pickle.dump(self.showids, f)

    def load_cache(self):
        logger.debug(u'Loading showids from cache...')
        with self.lock:
            with open(self.showids_cache, 'r') as f:
                self.showids = pickle.load(f)

    def query(self, season, episode, languages, filepath, tvdbid=None, series=None):
        self.load_cache()
        if series:
            if series.lower() in self.showids:  # from cache
                request_id = self.showids[series.lower()]
                logger.debug(u'Retreived showid %d for %s from cache' % (request_id, series))
            else:  # query to get showid
                logger.debug(u'Getting showid from show name %s...' % series)
                r = self.session.get('%sGetShowByName/%s' % (self.server_url, urllib.quote(series.lower())))
                if r.status_code != 200:
                    logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
                    return []
                soup = BeautifulSoup.BeautifulStoneSoup(r.content)
                if soup.status.contents[0] == 'false':
                    logger.debug(u'Could not find show %s' % series)
                    return []
                request_id = int(soup.showid.contents[0])
                self.showids[series.lower()] = request_id
                self.save_cache()
            request_source = 'showid'
            request_is_tvdbid = 'false'
        elif tvdbid:
            request_id = tvdbid
            request_source = 'tvdbid'
            request_is_tvdbid = 'true'
        else:
            raise ServiceError('One or more parameter missing')
        subtitles = []
        for language in languages:
            logger.debug(u'Getting subtitles for %s %d season %d episode %d with language %s' % (request_source, request_id, season, episode, language))
            r = self.session.get('%sGetAllSubsFor/%s/%s/%s/%s/%s' % (self.server_url, request_id, season, episode, language, request_is_tvdbid))
            if r.status_code != 200:
                logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
                return []
            soup = BeautifulSoup.BeautifulStoneSoup(r.content)
            if soup.status.contents[0] == 'false':
                logger.debug(u'Could not find subtitles for %s %d season %d episode %d with language %s' % (request_source, request_id, season, episode, language))
                continue
            path = get_subtitle_path(filepath, language, self.config.multi)
            for result in soup.results('result'):
                subtitle = ResultSubtitle(path, language, service=self.__class__.__name__.lower(), link=result.downloadlink.contents[0],
                                          release=to_unicode(result.filename.contents[0]))
                subtitles.append(subtitle)
        return subtitles

    def list(self, video, languages):
        if not self.check_validity(video, languages):
            return []
        results = self.query(video.season, video.episode, languages, video.path or video.release, video.tvdbid, video.series)
        return results


Service = BierDopje

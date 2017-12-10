# -*- coding: utf-8 -*-
# Copyright 2012 Ofir123 <ofirbrukner@gmail.com>
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
from ..language import language_set
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..videos import Episode, Movie
from ..utils import to_unicode

import bisect
import logging

from urllib import urlencode

logger = logging.getLogger(__name__)


class Subscenter(ServiceBase):
    server = 'http://www.cinemast.org/he/cinemast/api/'
    api_based = True
    languages = language_set(['he'])
    videos = [Episode, Movie]
    require_video = False

    default_username = 'subliminal@gmail.com'
    default_password = 'subliminal'

    def __init__(self, config=None):
        super(Subscenter, self).__init__(config)
        self.token = None
        self.user_id = None

    def init(self):
        super(Subscenter, self).init()
        logger.debug('Logging in')
        url = self.server_url + 'login/'

        # actual login
        data = {'username': self.default_username, 'password': self.default_password}
        r = self.session.post(url, data=urlencode(data), allow_redirects=False, timeout=10)

        if r.status_code != 200:
            raise ServiceError('Login failed')

        try:
            result = r.json()
            if 'token' not in result:
                raise ServiceError('Login failed')

            logger.info('Logged in')
            self.user_id = r.json().get('user')
            self.token = r.json().get('token')
        except ValueError:
            raise ServiceError('Login failed')

    def terminate(self):
        super(Subscenter, self).terminate()
        if self.token or self.user_id:
            logger.info('Logged out')
            self.token = None
            self.user_id = None

    def list_checked(self, video, languages):
        series = None
        season = None
        episode = None
        title = video.title
        year = video.year
        if isinstance(video, Episode):
            series = video.series
            season = video.season
            episode = video.episode
        return self.query(video.path or video.release, languages, series, season, episode, title, year)

    def query(self, filepath, languages=None, series=None, season=None, episode=None, title=None, year=None):
        logger.debug(u'Getting subtitles for {0} season {1} episode {2} with languages {3}'.format(
            series, season, episode, languages))

        query = {
            'user': self.user_id,
            'token': self.token
        }

        # episode
        if season and episode:
            query['q'] = series
            query['type'] = 'series'
            query['season'] = season
            query['episode'] = episode
        elif title:
            query['q'] = title
            query['type'] = 'movies'
            if year:
                query['year_start'] = year - 1
                query['year_end'] = year
        else:
            raise ServiceError('One or more parameters are missing')

        # get the list of subtitles
        logger.debug('Getting the list of subtitles')
        url = self.server_url + 'search/'
        r = self.session.post(url, data=urlencode(query))
        r.raise_for_status()

        try:
            results = r.json()
        except ValueError:
            return {}

        # loop over results
        subtitles = {}
        for group_data in results.get('data', []):
            for language_code, subtitles_data in group_data.get('subtitles', {}).items():
                language_object = self.get_language(language_code)

                for subtitle_item in subtitles_data:
                    # read the item
                    subtitle_id = subtitle_item['id']
                    subtitle_key = subtitle_item['key']
                    release = subtitle_item['version']

                    subtitle_path = get_subtitle_path(filepath, language_object, self.config.multi)
                    download_link = self.server_url + 'subtitle/download/{0}/?v={1}&key={2}&sub_id={3}'.format(
                        language_code, release, subtitle_key, subtitle_id)
                    # Add the release and increment downloaded count if we already have the subtitle.
                    if subtitle_id in subtitles:
                        logger.debug('Found additional release {0} for subtitle {1}'.format(
                            release, subtitle_id))
                        bisect.insort_left(subtitles[subtitle_id].release, release)  # Deterministic order.
                        continue
                    # Otherwise create it.
                    subtitle = ResultSubtitle(subtitle_path, language_object, self.__class__.__name__.lower(),
                                              download_link, release=to_unicode(release))
                    logger.debug('Found subtitle %r', subtitle)
                    subtitles[subtitle_id] = subtitle

        return subtitles.values()

    def download(self, subtitle):
        data = {
            'user': self.user_id,
            'token': self.token
        }
        self.download_zip_file(subtitle.link, subtitle.path, data=urlencode(data))
        return subtitle


Service = Subscenter

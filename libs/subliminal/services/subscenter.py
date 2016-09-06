# -*- coding: utf-8 -*-
# Copyright 2012 Ofir Brukner <ofirbrukner@gmail.com>
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
from ..utils import to_unicode, get_keywords
from bs4 import BeautifulSoup
import bisect
import json
import logging

logger = logging.getLogger(__name__)


class Subscenter(ServiceBase):
    server = 'http://www.subscenter.co/he/'
    api_based = False
    languages = language_set(['he'])
    videos = [Episode, Movie]
    require_video = False

    def _search_url_title(self, title, kind):
        """Search the URL title for the given `title`.

        :param str title: title to search for.
        :param str kind: kind of the title, ``movie`` or ``series``.
        :return: the URL version of the title.
        :rtype: str or None
        """
        # make the search
        logger.info('Searching title name for %r', title)
        r = self.session.get(self.server + 'subtitle/search/', params={'q': title}, allow_redirects=False, timeout=10)
        r.raise_for_status()

        # if redirected, get the url title from the Location header
        if r.is_redirect:
            parts = r.headers['Location'].split('/')

            # check kind
            if parts[-3] == kind:
                return parts[-2]

            return None

        # otherwise, get the first valid suggestion
        soup = BeautifulSoup(r.content, ['lxml', 'html.parser'])
        suggestions = soup.select('#processes div.generalWindowTop a')
        logger.debug('Found %d suggestions', len(suggestions))
        for suggestion in suggestions:
            parts = suggestion.attrs['href'].split('/')

            # check kind
            if parts[-3] == kind:
                return parts[-2]

    def list_checked(self, video, languages):
        series = None
        season = None
        episode = None
        title = video.title
        if isinstance(video, Episode):
            series = video.series
            season = video.season
            episode = video.episode
        return self.query(video.path or video.release, languages, get_keywords(video.guess), series, season,
                          episode, title)

    def query(self, filepath, languages=None, keywords=None, series=None, season=None, episode=None, title=None):
        logger.debug(u'Getting subtitles for {0} season {1} episode {2} with languages {3}'.format(
            series, season, episode, languages))
        # Set the correct parameters depending on the kind.
        if series and season and episode:
            url_series = self._search_url_title(series, 'series')
            url = self.server + 'cst/data/series/sb/{}/{}/{}/'.format(url_series, season, episode)
        elif title:
            url_title = self._search_url_title(title, 'movie')
            url = self.server + 'cst/data/movie/sb/{}/'.format(url_title)
        else:
            raise ServiceError('One or more parameters are missing')
        logger.debug('Searching subtitles for title {0}, season {1}, episode {2}'.format(title, season, episode))
        response = self.session.get(url)
        if response.status_code != 200:
            raise ServiceError('Request failed with status code {0}'.format(response.status_code))
        # Loop over results.
        subtitles = dict()
        response_json = json.loads(response.content)
        for language_code, language_data in response_json.items():
            language_object = self.get_language(language_code)
            if language_object in self.languages and language_object in languages:
                for quality_data in language_data.values():
                    for quality, subtitles_data in quality_data.items():
                        for subtitle_item in subtitles_data.values():
                            # Read the item.
                            subtitle_id = subtitle_item['id']
                            subtitle_key = subtitle_item['key']
                            release = subtitle_item['subtitle_version']
                            subtitle_path = get_subtitle_path(filepath, language_object, self.config.multi)
                            download_link = self.server_url + 'subtitle/download/{0}/{1}/?v={2}&key={3}'.format(
                                language_code, subtitle_id, release, subtitle_key)
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
        self.download_zip_file(subtitle.link, subtitle.path)
        return subtitle


Service = Subscenter

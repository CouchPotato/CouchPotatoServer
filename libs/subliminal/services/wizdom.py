# -*- coding: utf-8 -*-
# Copyright 2017 Ofir123 <ofirbrukner@gmail.com>
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

logger = logging.getLogger(__name__)


class Wizdom(ServiceBase):
    server = 'http://wizdom.xyz'
    api_based = True
    languages = language_set(['he'])
    videos = [Episode, Movie]
    require_video = False

    _tmdb_api_key = 'a51ee051bcd762543373903de296e0a3'

    def _search_imdb_id(self, title, year, is_movie):
        """Search the IMDB ID for the given `title` and `year`.

        :param str title: title to search for.
        :param int year: year to search for (or 0 if not relevant).
        :param bool is_movie: If True, IMDB ID will be searched for in TMDB instead of Wizdom.
        :return: the IMDB ID for the given title and year (or None if not found).
        :rtype: str
        """
        # make the search
        logger.info('Searching IMDB ID for %r%r', title, '' if not year else ' ({})'.format(year))
        category = 'movie' if is_movie else 'tv'
        title = title.replace('\'', '')
        # get TMDB ID first
        r = self.session.get('http://api.tmdb.org/3/search/{}?api_key={}&query={}{}&language=en'.format(
            category, self._tmdb_api_key, title, '' if not year else '&year={}'.format(year)))
        r.raise_for_status()
        tmdb_results = r.json().get('results')
        if tmdb_results:
            tmdb_id = tmdb_results[0].get('id')
            if tmdb_id:
                # get actual IMDB ID from TMDB
                r = self.session.get('http://api.tmdb.org/3/{}/{}{}?api_key={}&language=en'.format(
                    category, tmdb_id, '' if is_movie else '/external_ids', self._tmdb_api_key))
                r.raise_for_status()
                return str(r.json().get('imdb_id', '')) or None
        return None

    def list_checked(self, video, languages):
        series = None
        season = None
        episode = None
        title = video.title
        imdb_id = video.imdbid
        year = video.year
        if isinstance(video, Episode):
            series = video.series
            season = video.season
            episode = video.episode
        return self.query(video.path or video.release, languages, series, season,
                          episode, title, imdb_id, year)

    def query(self, filepath, languages=None, series=None, season=None, episode=None, title=None, imdbid=None,
              year=None):
        logger.debug(u'Getting subtitles for {0} season {1} episode {2} with languages {3}'.format(
            series, season, episode, languages))
        # search for the IMDB ID if needed
        is_movie = not (series and season and episode)
        if is_movie and not title:
            raise ServiceError('One or more parameters are missing')
        # for TV series, we need the series IMDB ID, and not the specific episode ID
        imdb_id = imdbid or self._search_imdb_id(title, year, is_movie)

        # search
        logger.debug(u'Using IMDB ID {0}'.format(imdb_id))
        url = 'http://json.{}/{}.json'.format(self.server_url, imdb_id)

        # get the list of subtitles
        logger.debug('Getting the list of subtitles')
        r = self.session.get(url)
        r.raise_for_status()
        try:
            results = r.json()
        except ValueError:
            return {}

        # filter irrelevant results
        if not is_movie:
            results = results.get('subs', {}).get(str(season), {}).get(str(episode), [])
        else:
            results = results.get('subs', [])

        # loop over results
        subtitles = dict()
        for result in results:
            language_object = self.get_language('heb')
            subtitle_id = result['id']
            release = result['version']
            subtitle_path = get_subtitle_path(filepath, language_object, self.config.multi)
            download_link = 'http://zip.{}/{}.zip'.format(self.server_url, subtitle_id)
            # add the release and increment downloaded count if we already have the subtitle
            if subtitle_id in subtitles:
                logger.debug(u'Found additional release {0} for subtitle {1}'.format(release, subtitle_id))
                bisect.insort_left(subtitles[subtitle_id].releases, release)  # deterministic order
                subtitles[subtitle_id].downloaded += 1
                continue
            # otherwise create it
            subtitle = ResultSubtitle(subtitle_path, language_object, self.__class__.__name__.lower(),
                                      download_link, release=to_unicode(release))
            logger.debug(u'Found subtitle {0}'.format(subtitle))
            subtitles[subtitle_id] = subtitle

        return subtitles.values()

    def download(self, subtitle):
        self.download_zip_file(subtitle.link, subtitle.path)
        return subtitle


Service = Wizdom

# -*- coding: utf-8 -*-
# Copyright 2012 Olivier Leveau <olifozzy@gmail.com>
# Copyright 2012 Antoine Bertin <diaoulael@gmail.com>
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
from ..cache import cachedmethod
from ..exceptions import DownloadFailedError
from ..language import Language, language_set
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..utils import get_keywords, split_keyword
from ..videos import Episode
from bs4 import BeautifulSoup
import logging
import os
import re


logger = logging.getLogger(__name__)


class Addic7ed(ServiceBase):
    server_url = 'http://www.addic7ed.com'
    api_based = False
    #TODO: Complete this
    languages = language_set(['ar', 'ca', 'de', 'el', 'en', 'es', 'eu', 'fr', 'ga', 'gl', 'he', 'hr', 'hu',
                              'it', 'pl', 'pt', 'ro', 'ru', 'se', 'pt-br'])
    language_map = {'Portuguese (Brazilian)': Language('por-BR'), 'Greek': Language('gre'),
                    'Spanish (Latin America)': Language('spa'), 'Galego': Language('glg'),
                    u'Català': Language('cat')}
    videos = [Episode]
    require_video = False
    required_features = ['permissive']

    @cachedmethod
    def get_series_id(self, name):
        """Get the show page and cache every show found in it"""
        r = self.session.get('%s/shows.php' % self.server_url)
        soup = BeautifulSoup(r.content, self.required_features)
        for html_series in soup.select('h3 > a'):
            series_name = html_series.text.lower()
            match = re.search('show/([0-9]+)', html_series['href'])
            if match is None:
                continue
            series_id = int(match.group(1))
            self.cache_for(self.get_series_id, args=(series_name,), result=series_id)
        return self.cached_value(self.get_series_id, args=(name,))

    def list_checked(self, video, languages):
        return self.query(video.path or video.release, languages, get_keywords(video.guess), video.series, video.season, video.episode)

    def query(self, filepath, languages, keywords, series, season, episode):
        logger.debug(u'Getting subtitles for %s season %d episode %d with languages %r' % (series, season, episode, languages))
        self.init_cache()
        try:
            series_id = self.get_series_id(series.lower())
        except KeyError:
            logger.debug(u'Could not find series id for %s' % series)
            return []
        r = self.session.get('%s/show/%d&season=%d' % (self.server_url, series_id, season))
        soup = BeautifulSoup(r.content, self.required_features)
        subtitles = []
        for row in soup('tr', {'class': 'epeven completed'}):
            cells = row('td')
            if int(cells[0].text.strip()) != season or int(cells[1].text.strip()) != episode:
                continue
            if cells[6].text.strip():
                logger.debug(u'Skipping hearing impaired')
                continue
            sub_status = cells[5].text.strip()
            if sub_status != 'Completed':
                logger.debug(u'Wrong subtitle status %s' % sub_status)
                continue
            sub_language = self.get_language(cells[3].text.strip())
            if sub_language not in languages:
                logger.debug(u'Language %r not in wanted languages %r' % (sub_language, languages))
                continue
            sub_keywords = split_keyword(cells[4].text.strip().lower())
            #TODO: Maybe allow empty keywords here? (same in Subtitulos)
            if not keywords & sub_keywords:
                logger.debug(u'None of subtitle keywords %r in %r' % (sub_keywords, keywords))
                continue
            sub_link = '%s/%s' % (self.server_url, cells[9].a['href'])
            sub_path = get_subtitle_path(filepath, sub_language, self.config.multi)
            subtitle = ResultSubtitle(sub_path, sub_language, self.__class__.__name__.lower(), sub_link, keywords=sub_keywords)
            subtitles.append(subtitle)
        return subtitles

    def download(self, subtitle):
        logger.info(u'Downloading %s in %s' % (subtitle.link, subtitle.path))
        try:
            r = self.session.get(subtitle.link, headers={'Referer': subtitle.link, 'User-Agent': self.user_agent})
            soup = BeautifulSoup(r.content, self.required_features)
            if soup.title is not None and u'Addic7ed.com' in soup.title.text.strip():
                raise DownloadFailedError('Download limit exceeded')
            with open(subtitle.path, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            logger.error(u'Download failed: %s' % e)
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            raise DownloadFailedError(str(e))
        logger.debug(u'Download finished')
        return subtitle


Service = Addic7ed

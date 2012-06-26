# -*- coding: utf-8 -*-
# Copyright 2012 Olivier Leveau <olifozzy@gmail.com>
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
from ..utils import get_keywords
from ..videos import Episode
from bs4 import BeautifulSoup
import logging
import os
import re


logger = logging.getLogger(__name__)


def match(pattern, string):
    try:
        return re.search(pattern, string).group(1)
    except AttributeError:
        logger.debug(u'Could not match %r on %r' % (pattern, string))
        return None


def matches(pattern, string):
    try:
        return re.search(pattern, string).group(1, 2)
    except AttributeError:
        logger.debug(u'Could not match %r on %r' % (pattern, string))
        return None


class Addic7ed(ServiceBase):
    server_url = 'http://www.addic7ed.com'
    api_based = False
    #TODO: Complete this
    languages = language_set(['ar', 'ca', 'de', 'el', 'en', 'es', 'eu', 'fr', 'ga', 'he', 'hr', 'hu', 'it',
                              'pl', 'pt', 'ro', 'ru', 'se', 'pt-br'])
    language_map = {'Portuguese (Brazilian)': Language('por-BR'), 'Greek': Language('gre'),
                    'Spanish (Latin America)': Language('spa'), }
    videos = [Episode]
    require_video = False
    required_features = ['permissive']

    @cachedmethod
    def get_likely_series_id(self, name):
        r = self.session.get('%s/shows.php' % self.server_url)
        soup = BeautifulSoup(r.content, self.required_features)
        for elem in soup.find_all('h3'):
            show_name = elem.a.text.lower()
            show_id = int(match('show/([0-9]+)', elem.a['href']))
            # we could just return the id of the queried show, but as we
            # already downloaded the whole page we might as well fill in the
            # information for all the shows
            self.cache_for(self.get_likely_series_id, args=(show_name,), result=show_id)
        return self.cached_value(self.get_likely_series_id, args=(name,))

    @cachedmethod
    def get_episode_url(self, series_id, season, number):
        """Get the Addic7ed id for the given episode. Raises KeyError if none
        could be found

        """
        # download the page of the show, contains ids for all episodes all seasons
        r = self.session.get('%s/show/%d' % (self.server_url, series_id))
        soup = BeautifulSoup(r.content, self.required_features)
        form = soup.find('form', attrs={'name': 'multidl'})
        for table in form.find_all('table'):
            for row in table.find_all('tr'):
                cell = row.find('td', 'MultiDldS')
                if not cell:
                    continue
                m = matches('/serie/.+/([0-9]+)/([0-9]+)/', cell.a['href'])
                if not m:
                    continue
                episode_url = cell.a['href']
                season_number = int(m[0])
                episode_number = int(m[1])
                # we could just return the url of the queried episode, but as we
                # already downloaded the whole page we might as well fill in the
                # information for all the episodes of the show
                self.cache_for(self.get_episode_url, args=(series_id, season_number, episode_number), result=episode_url)
        # raises KeyError if not found
        return self.cached_value(self.get_episode_url, args=(series_id, season, number))

    # Do not cache this method in order to always check for the most recent
    # subtitles
    def get_sub_urls(self, episode_url):
        suburls = []
        r = self.session.get('%s/%s' % (self.server_url, episode_url))
        epsoup = BeautifulSoup(r.content, self.required_features)
        for releaseTable in epsoup.find_all('table', 'tabel95'):
            releaseRow = releaseTable.find('td', 'NewsTitle')
            if not releaseRow:
                continue
            release = releaseRow.text.strip()
            for row in releaseTable.find_all('tr'):
                link = row.find('a', 'buttonDownload')
                if not link:
                    continue
                if 'href' not in link.attrs or not (link['href'].startswith('/original') or link['href'].startswith('/updated')):
                    continue
                suburl = link['href']
                lang = self.get_language(row.find('td', 'language').text.strip())
                result = {'suburl': suburl, 'language': lang, 'release': release}
                suburls.append(result)
        return suburls

    def list_checked(self, video, languages):
        return self.query(video.path or video.release, languages, get_keywords(video.guess), video.series, video.season, video.episode)

    def query(self, filepath, languages, keywords, series, season, episode):
        logger.debug(u'Getting subtitles for %s season %d episode %d with languages %r' % (series, season, episode, languages))
        self.init_cache()
        try:
            sid = self.get_likely_series_id(series.lower())
        except KeyError:
            logger.debug(u'Could not find series id for %s' % series)
            return []
        try:
            ep_url = self.get_episode_url(sid, season, episode)
        except KeyError:
            logger.debug(u'Could not find episode id for %s season %d episode %d' % (series, season, episode))
            return []
        suburls = self.get_sub_urls(ep_url)
        # filter the subtitles with our queried languages
        subtitles = []
        for suburl in suburls:
            language = suburl['language']
            if language not in languages:
                continue
            path = get_subtitle_path(filepath, language, self.config.multi)
            subtitle = ResultSubtitle(path, language, self.__class__.__name__.lower(), '%s/%s' % (self.server_url, suburl['suburl']),
                                      keywords=[suburl['release']])
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

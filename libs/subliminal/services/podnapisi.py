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
from ..exceptions import ServiceError, DownloadFailedError
from ..language import language_set, Language
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..utils import to_unicode
from ..videos import Episode, Movie
from hashlib import md5, sha256
import logging
import xmlrpclib


logger = logging.getLogger(__name__)


class Podnapisi(ServiceBase):
    server_url = 'http://ssp.podnapisi.net:8000'
    api_based = True
    languages = language_set(['ar', 'be', 'bg', 'bs', 'ca', 'ca', 'cs', 'da', 'de', 'el', 'en',
                              'es', 'et', 'fa', 'fi', 'fr', 'ga', 'he', 'hi', 'hr', 'hu', 'id',
                              'is', 'it', 'ja', 'ko', 'lt', 'lv', 'mk', 'ms', 'nl', 'nn', 'pl',
                              'pt', 'ro', 'ru', 'sk', 'sl', 'sq', 'sr', 'sv', 'th', 'tr', 'uk',
                              'vi', 'zh', 'es-ar', 'pt-br'])
    language_map = {'jp': Language('jpn'), Language('jpn'): 'jp',
                    'gr': Language('gre'), Language('gre'): 'gr',
                    'pb': Language('por-BR'), Language('por-BR'): 'pb',
                    'ag': Language('spa-AR'), Language('spa-AR'): 'ag',
                    'cyr': Language('srp')}
    videos = [Episode, Movie]
    require_video = True

    def __init__(self, config=None):
        super(Podnapisi, self).__init__(config)
        self.server = xmlrpclib.ServerProxy(self.server_url)
        self.token = None

    def init(self):
        super(Podnapisi, self).init()
        result = self.server.initiate(self.user_agent)
        if result['status'] != 200:
            raise ServiceError('Initiate failed')
        username = 'python_subliminal'
        password = sha256(md5('XWFXQ6gE5Oe12rv4qxXX').hexdigest() + result['nonce']).hexdigest()
        self.token = result['session']
        result = self.server.authenticate(self.token, username, password)
        if result['status'] != 200:
            raise ServiceError('Authenticate failed')

    def terminate(self):
        super(Podnapisi, self).terminate()

    def query(self, filepath, languages, moviehash):
        results = self.server.search(self.token, [moviehash])
        if results['status'] != 200:
            logger.error('Search failed with error code %d' % results['status'])
            return []
        if not results['results'] or not results['results'][moviehash]['subtitles']:
            logger.debug(u'Could not find subtitles for %r with token %s' % (moviehash, self.token))
            return []
        subtitles = []
        for result in results['results'][moviehash]['subtitles']:
            language = self.get_language(result['lang'])
            if language not in languages:
                continue
            path = get_subtitle_path(filepath, language, self.config.multi)
            subtitle = ResultSubtitle(path, language, self.__class__.__name__.lower(), result['id'],
                                      release=to_unicode(result['release']), confidence=result['weight'])
            subtitles.append(subtitle)
        if not subtitles:
            return []
        # Convert weight to confidence
        max_weight = float(max([s.confidence for s in subtitles]))
        min_weight = float(min([s.confidence for s in subtitles]))
        for subtitle in subtitles:
            if max_weight == 0 and min_weight == 0:
                subtitle.confidence = 1.0
            else:
                subtitle.confidence = (subtitle.confidence - min_weight) / (max_weight - min_weight)
        return subtitles

    def list_checked(self, video, languages):
        results = self.query(video.path, languages, video.hashes['OpenSubtitles'])
        return results

    def download(self, subtitle):
        results = self.server.download(self.token, [subtitle.link])
        if results['status'] != 200:
            raise DownloadFailedError()
        subtitle.link = 'http://www.podnapisi.net/static/podnapisi/' + results['names'][0]['filename']
        self.download_file(subtitle.link, subtitle.path)
        return subtitle


Service = Podnapisi

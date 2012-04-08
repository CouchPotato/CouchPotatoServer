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
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..videos import Episode, Movie
from ..utils import to_unicode
import gzip
import logging
import os.path
import xmlrpclib


logger = logging.getLogger(__name__)


class OpenSubtitles(ServiceBase):
    server_url = 'http://api.opensubtitles.org/xml-rpc'
    api_based = True
    languages = {'aa': 'aar', 'ab': 'abk', 'af': 'afr', 'ak': 'aka', 'sq': 'alb', 'am': 'amh', 'ar': 'ara',
                 'an': 'arg', 'hy': 'arm', 'as': 'asm', 'av': 'ava', 'ae': 'ave', 'ay': 'aym', 'az': 'aze',
                 'ba': 'bak', 'bm': 'bam', 'eu': 'baq', 'be': 'bel', 'bn': 'ben', 'bh': 'bih', 'bi': 'bis',
                 'bs': 'bos', 'br': 'bre', 'bg': 'bul', 'my': 'bur', 'ca': 'cat', 'ch': 'cha', 'ce': 'che',
                 'zh': 'chi', 'cu': 'chu', 'cv': 'chv', 'kw': 'cor', 'co': 'cos', 'cr': 'cre', 'cs': 'cze',
                 'da': 'dan', 'dv': 'div', 'nl': 'dut', 'dz': 'dzo', 'en': 'eng', 'eo': 'epo', 'et': 'est',
                 'ee': 'ewe', 'fo': 'fao', 'fj': 'fij', 'fi': 'fin', 'fr': 'fre', 'fy': 'fry', 'ff': 'ful',
                 'ka': 'geo', 'de': 'ger', 'gd': 'gla', 'ga': 'gle', 'gl': 'glg', 'gv': 'glv', 'el': 'ell',
                 'gn': 'grn', 'gu': 'guj', 'ht': 'hat', 'ha': 'hau', 'he': 'heb', 'hz': 'her', 'hi': 'hin',
                 'ho': 'hmo', 'hr': 'hrv', 'hu': 'hun', 'ig': 'ibo', 'is': 'ice', 'io': 'ido', 'ii': 'iii',
                 'iu': 'iku', 'ie': 'ile', 'ia': 'ina', 'id': 'ind', 'ik': 'ipk', 'it': 'ita', 'jv': 'jav',
                 'ja': 'jpn', 'kl': 'kal', 'kn': 'kan', 'ks': 'kas', 'kr': 'kau', 'kk': 'kaz', 'km': 'khm',
                 'ki': 'kik', 'rw': 'kin', 'ky': 'kir', 'kv': 'kom', 'kg': 'kon', 'ko': 'kor', 'kj': 'kua',
                 'ku': 'kur', 'lo': 'lao', 'la': 'lat', 'lv': 'lav', 'li': 'lim', 'ln': 'lin', 'lt': 'lit',
                 'lb': 'ltz', 'lu': 'lub', 'lg': 'lug', 'mk': 'mac', 'mh': 'mah', 'ml': 'mal', 'mi': 'mao',
                 'mr': 'mar', 'ms': 'may', 'mg': 'mlg', 'mt': 'mlt', 'mo': 'mol', 'mn': 'mon', 'na': 'nau',
                 'nv': 'nav', 'nr': 'nbl', 'nd': 'nde', 'ng': 'ndo', 'ne': 'nep', 'nn': 'nno', 'nb': 'nob',
                 'no': 'nor', 'ny': 'nya', 'oc': 'oci', 'oj': 'oji', 'or': 'ori', 'om': 'orm', 'os': 'oss',
                 'pa': 'pan', 'fa': 'per', 'pi': 'pli', 'pl': 'pol', 'pt': 'por', 'ps': 'pus', 'qu': 'que',
                 'rm': 'roh', 'rn': 'run', 'ru': 'rus', 'sg': 'sag', 'sa': 'san', 'sr': 'scc', 'si': 'sin',
                 'sk': 'slo', 'sl': 'slv', 'se': 'sme', 'sm': 'smo', 'sn': 'sna', 'sd': 'snd', 'so': 'som',
                 'st': 'sot', 'es': 'spa', 'sc': 'srd', 'ss': 'ssw', 'su': 'sun', 'sw': 'swa', 'sv': 'swe',
                 'ty': 'tah', 'ta': 'tam', 'tt': 'tat', 'te': 'tel', 'tg': 'tgk', 'tl': 'tgl', 'th': 'tha',
                 'bo': 'tib', 'ti': 'tir', 'to': 'ton', 'tn': 'tsn', 'ts': 'tso', 'tk': 'tuk', 'tr': 'tur',
                 'tw': 'twi', 'ug': 'uig', 'uk': 'ukr', 'ur': 'urd', 'uz': 'uzb', 've': 'ven', 'vi': 'vie',
                 'vo': 'vol', 'cy': 'wel', 'wa': 'wln', 'wo': 'wol', 'xh': 'xho', 'yi': 'yid', 'yo': 'yor',
                 'za': 'zha', 'zu': 'zul', 'ro': 'rum', 'po': 'pob', 'un': 'unk', 'ay': 'ass'}
    reverted_languages = False
    videos = [Episode, Movie]
    require_video = False
    confidence_order = ['moviehash', 'imdbid', 'fulltext']

    def __init__(self, config=None):
        super(OpenSubtitles, self).__init__(config)
        self.server = xmlrpclib.ServerProxy(self.server_url)
        self.token = None

    def init(self):
        super(OpenSubtitles, self).init()
        result = self.server.LogIn('', '', 'eng', self.user_agent)
        if result['status'] != '200 OK':
            raise ServiceError('Login failed')
        self.token = result['token']

    def terminate(self):
        super(OpenSubtitles, self).terminate()
        if self.token:
            self.server.LogOut(self.token)

    def query(self, filepath, languages, moviehash=None, size=None, imdbid=None, query=None):
        searches = []
        if moviehash and size:
            searches.append({'moviehash': moviehash, 'moviebytesize': size})
        if imdbid:
            searches.append({'imdbid': imdbid})
        if query:
            searches.append({'query': query})
        if not searches:
            raise ServiceError('One or more parameter missing')
        for search in searches:
            search['sublanguageid'] = ','.join([self.get_language(l) for l in languages])
        logger.debug(u'Getting subtitles %r with token %s' % (searches, self.token))
        results = self.server.SearchSubtitles(self.token, searches)
        if not results['data']:
            logger.debug(u'Could not find subtitles for %r with token %s' % (searches, self.token))
            return []
        subtitles = []
        for result in results['data']:
            language = self.get_revert_language(result['SubLanguageID'])
            path = get_subtitle_path(filepath, language, self.config.multi)
            confidence = 1 - float(self.confidence_order.index(result['MatchedBy'])) / float(len(self.confidence_order))
            subtitle = ResultSubtitle(path, language, service=self.__class__.__name__.lower(), link=result['SubDownloadLink'],
                                      release=to_unicode(result['SubFileName']), confidence=confidence)
            subtitles.append(subtitle)
        return subtitles

    def list(self, video, languages):
        if not self.check_validity(video, languages):
            return []
        results = []
        if video.exists:
            results = self.query(video.path or video.release, languages, moviehash=video.hashes['OpenSubtitles'], size=str(video.size))
        elif video.imdbid:
            results = self.query(video.path or video.release, languages, imdbid=video.imdbid)
        elif isinstance(video, Episode):
            results = self.query(video.path or video.release, languages, query=video.series)
        elif isinstance(video, Movie):
            results = self.query(video.path or video.release, languages, query=video.title)
        return results

    def download(self, subtitle):
        #TODO: Use OpenSubtitles DownloadSubtitles method
        try:
            self.download_file(subtitle.link, subtitle.path + '.gz')
            with open(subtitle.path, 'wb') as dump:
                gz = gzip.open(subtitle.path + '.gz')
                dump.write(gz.read())
                gz.close()
        except Exception as e:
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            raise DownloadFailedError(str(e))
        finally:
            if os.path.exists(subtitle.path + '.gz'):
                os.remove(subtitle.path + '.gz')
        return subtitle


Service = OpenSubtitles

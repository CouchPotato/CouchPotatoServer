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
from ..language import Language, language_set
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..utils import to_unicode
from ..videos import Episode, Movie
import gzip
import logging
import os.path
import xmlrpclib


logger = logging.getLogger(__name__)


class OpenSubtitles(ServiceBase):
    server_url = 'http://api.opensubtitles.org/xml-rpc'
    api_based = True
    # Source: http://www.opensubtitles.org/addons/export_languages.php
    languages = language_set(['aar', 'abk', 'ace', 'ach', 'ada', 'ady', 'afa', 'afh', 'afr', 'ain', 'aka', 'akk',
                              'alb', 'ale', 'alg', 'alt', 'amh', 'ang', 'apa', 'ara', 'arc', 'arg', 'arm', 'arn',
                              'arp', 'art', 'arw', 'asm', 'ast', 'ath', 'aus', 'ava', 'ave', 'awa', 'aym', 'aze',
                              'bad', 'bai', 'bak', 'bal', 'bam', 'ban', 'baq', 'bas', 'bat', 'bej', 'bel', 'bem',
                              'ben', 'ber', 'bho', 'bih', 'bik', 'bin', 'bis', 'bla', 'bnt', 'bos', 'bra', 'bre',
                              'btk', 'bua', 'bug', 'bul', 'bur', 'byn', 'cad', 'cai', 'car', 'cat', 'cau', 'ceb',
                              'cel', 'cha', 'chb', 'che', 'chg', 'chi', 'chk', 'chm', 'chn', 'cho', 'chp', 'chr',
                              'chu', 'chv', 'chy', 'cmc', 'cop', 'cor', 'cos', 'cpe', 'cpf', 'cpp', 'cre', 'crh',
                              'crp', 'csb', 'cus', 'cze', 'dak', 'dan', 'dar', 'day', 'del', 'den', 'dgr', 'din',
                              'div', 'doi', 'dra', 'dua', 'dum', 'dut', 'dyu', 'dzo', 'efi', 'egy', 'eka', 'ell',
                              'elx', 'eng', 'enm', 'epo', 'est', 'ewe', 'ewo', 'fan', 'fao', 'fat', 'fij', 'fil',
                              'fin', 'fiu', 'fon', 'fre', 'frm', 'fro', 'fry', 'ful', 'fur', 'gaa', 'gay', 'gba',
                              'gem', 'geo', 'ger', 'gez', 'gil', 'gla', 'gle', 'glg', 'glv', 'gmh', 'goh', 'gon',
                              'gor', 'got', 'grb', 'grc', 'grn', 'guj', 'gwi', 'hai', 'hat', 'hau', 'haw', 'heb',
                              'her', 'hil', 'him', 'hin', 'hit', 'hmn', 'hmo', 'hrv', 'hun', 'hup', 'iba', 'ibo',
                              'ice', 'ido', 'iii', 'ijo', 'iku', 'ile', 'ilo', 'ina', 'inc', 'ind', 'ine', 'inh',
                              'ipk', 'ira', 'iro', 'ita', 'jav', 'jpn', 'jpr', 'jrb', 'kaa', 'kab', 'kac', 'kal',
                              'kam', 'kan', 'kar', 'kas', 'kau', 'kaw', 'kaz', 'kbd', 'kha', 'khi', 'khm', 'kho',
                              'kik', 'kin', 'kir', 'kmb', 'kok', 'kom', 'kon', 'kor', 'kos', 'kpe', 'krc', 'kro',
                              'kru', 'kua', 'kum', 'kur', 'kut', 'lad', 'lah', 'lam', 'lao', 'lat', 'lav', 'lez',
                              'lim', 'lin', 'lit', 'lol', 'loz', 'ltz', 'lua', 'lub', 'lug', 'lui', 'lun', 'luo',
                              'lus', 'mac', 'mad', 'mag', 'mah', 'mai', 'mak', 'mal', 'man', 'mao', 'map', 'mar',
                              'mas', 'may', 'mdf', 'mdr', 'men', 'mga', 'mic', 'min', 'mkh', 'mlg', 'mlt', 'mnc',
                              'mni', 'mno', 'moh', 'mon', 'mos', 'mun', 'mus', 'mwl', 'mwr', 'myn', 'myv', 'nah',
                              'nai', 'nap', 'nau', 'nav', 'nbl', 'nde', 'ndo', 'nds', 'nep', 'new', 'nia', 'nic',
                              'niu', 'nno', 'nob', 'nog', 'non', 'nor', 'nso', 'nub', 'nwc', 'nya', 'nym', 'nyn',
                              'nyo', 'nzi', 'oci', 'oji', 'ori', 'orm', 'osa', 'oss', 'ota', 'oto', 'paa', 'pag',
                              'pal', 'pam', 'pan', 'pap', 'pau', 'peo', 'per', 'phi', 'phn', 'pli', 'pol', 'pon',
                              'por', 'pra', 'pro', 'pus', 'que', 'raj', 'rap', 'rar', 'roa', 'roh', 'rom', 'rum',
                              'run', 'rup', 'rus', 'sad', 'sag', 'sah', 'sai', 'sal', 'sam', 'san', 'sas', 'sat',
                              'scn', 'sco', 'sel', 'sem', 'sga', 'sgn', 'shn', 'sid', 'sin', 'sio', 'sit', 'sla',
                              'slo', 'slv', 'sma', 'sme', 'smi', 'smj', 'smn', 'smo', 'sms', 'sna', 'snd', 'snk',
                              'sog', 'som', 'son', 'sot', 'spa', 'srd', 'srp', 'srr', 'ssa', 'ssw', 'suk', 'sun',
                              'sus', 'sux', 'swa', 'swe', 'syr', 'tah', 'tai', 'tam', 'tat', 'tel', 'tem', 'ter',
                              'tet', 'tgk', 'tgl', 'tha', 'tib', 'tig', 'tir', 'tiv', 'tkl', 'tlh', 'tli', 'tmh',
                              'tog', 'ton', 'tpi', 'tsi', 'tsn', 'tso', 'tuk', 'tum', 'tup', 'tur', 'tut', 'tvl',
                              'twi', 'tyv', 'udm', 'uga', 'uig', 'ukr', 'umb', 'urd', 'uzb', 'vai', 'ven', 'vie',
                              'vol', 'vot', 'wak', 'wal', 'war', 'was', 'wel', 'wen', 'wln', 'wol', 'xal', 'xho',
                              'yao', 'yap', 'yid', 'yor', 'ypk', 'zap', 'zen', 'zha', 'znd', 'zul', 'zun',
                              'por-BR', 'rum-MD'])
    language_map = {'mol': Language('rum-MD'), 'scc': Language('srp'), 'pob': Language('por-BR'),
                    Language('rum-MD'): 'mol', Language('srp'): 'scc', Language('por-BR'): 'pob'}
    language_code = 'alpha3'
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
            search['sublanguageid'] = ','.join(self.get_code(l) for l in languages)
        logger.debug(u'Getting subtitles %r with token %s' % (searches, self.token))
        results = self.server.SearchSubtitles(self.token, searches)
        if not results['data']:
            logger.debug(u'Could not find subtitles for %r with token %s' % (searches, self.token))
            return []
        subtitles = []
        for result in results['data']:
            language = self.get_language(result['SubLanguageID'])
            path = get_subtitle_path(filepath, language, self.config.multi)
            confidence = 1 - float(self.confidence_order.index(result['MatchedBy'])) / float(len(self.confidence_order))
            subtitle = ResultSubtitle(path, language, self.__class__.__name__.lower(), result['SubDownloadLink'],
                                      release=to_unicode(result['SubFileName']), confidence=confidence)
            subtitles.append(subtitle)
        return subtitles

    def list_checked(self, video, languages):
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

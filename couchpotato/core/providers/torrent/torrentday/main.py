from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import tryInt, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import ResultList
from couchpotato.core.providers.torrent.base import TorrentProvider
import time
import traceback

log = CPLog(__name__)


class TorrentDay(TorrentProvider):

    urls = {
        'test': 'http://www.td.af/',
        'login' : 'http://www.td.af/torrents/',
        'detail': 'http://www.td.af/details.php?id=%s',
        'search': 'http://www.td.af/V3/API/API.php',
        'download': 'http://www.td.af/download.php/%s/%s',
    }

    cat_ids = [
        ([11], ['720p', '1080p']),
        ([1, 21, 25], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
        ([3], ['dvdr']),
        ([5], ['bd50']),
    ]

    http_time_between_calls = 1 #seconds

    def search(self, movie, quality):

        if self.isDisabled() or (not self.login_opener and not self.login()):
            return []

        q = '"%s %s"' % (getTitle(movie['library']), movie['library']['year'])

        results = ResultList(self, movie, quality, imdb_results = True)

        params = {
            '/browse.php?': None,
            'cata': 'yes',
            'jxt': 8,
            'jxw': 'b',
            'search': q,
        }

        data = self.getJsonData(self.urls['search'], params = params, opener = self.login_opener)
        try: torrents = data.get('Fs', [])[0].get('Cn', {}).get('torrents', [])
        except: return []

        for torrent in torrents:

            results.append({
                'id': torrent['id'],
                'name': torrent['name'],
                'url': self.urls['download'] % (torrent['id'], torrent['fname']),
                'detail_url': self.urls['detail'] % torrent['id'],
                'size': self.parseSize(torrent.get('size')),
                'seeders': tryInt(torrent.get('seed')),
                'leechers': tryInt(torrent.get('leech')),
                'download': self.loginDownload,
                'get_more_info': self.getMoreInfo,
            })

        return results

    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'submit': 'submit',
        })

    def getMoreInfo(self, item):
        full_description = self.getCache('sceneaccess.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('div', attrs = {'id':'details_table'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider

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

    def _searchOnTitle(self, title, movie, quality, results):

        q = '"%s %s"' % (title, movie['library']['year'])

        params = {
            '/browse.php?': None,
            'cata': 'yes',
            'jxt': 8,
            'jxw': 'b',
            'search': q,
        }

        data = self.getJsonData(self.urls['search'], params = params, opener = self.login_opener)
        try: torrents = data.get('Fs', [])[0].get('Cn', {}).get('torrents', [])
        except: return

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
            })

    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'submit': 'submit',
        })

from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider

log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'http://www.td.af/',
        'login': 'http://www.td.af/torrents/',
        'login_check': 'http://www.torrentday.com/userdetails.php',
        'detail': 'http://www.td.af/details.php?id=%s',
        'search': 'http://www.td.af/V3/API/API.php',
        'download': 'http://www.td.af/download.php/%s/%s',
    }

    http_time_between_calls = 1 #seconds

    def _search(self, media, quality, results):

        query = self.buildUrl(media)

        data = {
            '/browse.php?': None,
            'cata': 'yes',
            'jxt': 8,
            'jxw': 'b',
            'search': query,
        }

        data = self.getJsonData(self.urls['search'], data = data)
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
            })

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'submit.x': 18,
            'submit.y': 11,
            'submit': 'submit',
        }

    def loginSuccess(self, output):
        return 'Password not correct' not in output

    def loginCheckSuccess(self, output):
        return 'logout.php' in output.lower()

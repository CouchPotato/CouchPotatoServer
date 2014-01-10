from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class HDBits(TorrentProvider):

    urls = {
        'test' : 'https://hdbits.org/',
        'login' : 'https://hdbits.org/login/doLogin/',
        'detail' : 'https://hdbits.org/details.php?id=%s&source=browse',
        'search' : 'https://hdbits.org/json_search.php?imdb=%s',
        'download' : 'https://hdbits.org/download.php/%s.torrent?id=%s&passkey=%s&source=details.browse',
        'login_check': 'http://hdbits.org/inbox.php',
    }

    http_time_between_calls = 1 #seconds

    def _search(self, movie, quality, results):

        data = self.getJsonData(self.urls['search'] % movie['library']['identifier'])

        if data:
            try:
                for result in data:
                    results.append({
                        'id': result['id'],
                        'name': result['title'],
                        'url': self.urls['download'] % (result['id'], result['id'], self.conf('passkey')),
                        'detail_url': self.urls['detail'] % result['id'],
                        'size': self.parseSize(result['size']),
                        'seeders': tryInt(result['seeder']),
                        'leechers': tryInt(result['leecher'])
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        data = self.getHTMLData('https://hdbits.org/login', cache_timeout = 0)

        bs = BeautifulSoup(data)
        secret = bs.find('input', attrs = {'name': 'lol'})['value']

        return {
            'uname': self.conf('username'),
            'password': self.conf('password'),
            'returnto': '/',
            'lol': secret
        }

    def loginSuccess(self, output):
        return '/logout.php' in output.lower()

    loginCheckSuccess = loginSuccess

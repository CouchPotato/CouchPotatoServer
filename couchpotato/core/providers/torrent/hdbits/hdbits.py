from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback
from bs4 import BeautifulSoup
import requests

log = CPLog(__name__)

class HDBits(TorrentProvider):

    urls = {
        'test' : 'http://www.hdbits.org/',
        'login' : 'https://hdbits.org/login/dologin/',
        'detail' : 'http://www.hdbits.org/details.php?id=%s&source=browse',
        'search' : 'http://www.hdbits.org/json_search.php?imdb=%s',
        'download' : 'http://hdbits.org/download.php/%s.torrent?id=%s&passkey=%s&source=details.browse',
    }

    http_time_between_calls = 1 #seconds

    def login(self):
        try:
            self.login_opener = requests.Session()
            payload = {'uname': self.conf('username'), 'password': self.conf('password'), 'lol': self._getLoginSecret()}
            self.login_opener.post(self.urls['login'], data=payload)

            return True
        except:
            log.error('Failed to login')

        return False

    def _search(self, movie, quality, results):
        log.debug('Session response: %s' % (self.response.cookies))
        if not self.login_opener and not self.login():
            return

        imdb_id = movie['library']['identifier']
        search = self.login_opener.get(self.urls['search'] % (imdb_id))

        j = search.json
        try:
            for result in j:
                url = self.urls['download'] % (result['title'], result['id'], self.conf('passkey'))
                detail = self.urls['detail'] % result['id']

                results.append({
                    'id': result['id'],
                    'name': result['title'],
                    'url': url,
                    'detail_url': detail,
                    'size': self.parseSize(result['size']),
                    'seeders': tryInt(result['seeder']),
                    'leechers': tryInt(result['leecher'])
                })

                log.debug('Results: %s' % (results))

        except:
            log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def _getLoginSecret(self):
        r = requests.get('https://hdbits.org/json_search.php')
        bs = BeautifulSoup(r.text)
        secret = bs.find('input', attrs = {'name': 'lol'})['value']

        log.debug('Secret key: %s' % (secret))

        return secret

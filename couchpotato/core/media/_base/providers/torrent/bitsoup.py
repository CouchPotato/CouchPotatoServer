import traceback

from bs4 import BeautifulSoup, SoupStrainer
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://www.bitsoup.me/',
        'login': 'https://www.bitsoup.me/takelogin.php',
        'login_check': 'https://www.bitsoup.me/my.php',
        'search': 'https://www.bitsoup.me/browse.php?%s',
        'baseurl': 'https://www.bitsoup.me/%s',
    }

    http_time_between_calls = 1  # Seconds
    only_tables_tags = SoupStrainer('table')

    torrent_name_cell = 1
    torrent_download_cell = 2

    def _searchOnTitle(self, title, movie, quality, results):

        url = self.urls['search'] % self.buildUrl(title, movie, quality)
        data = self.getHTMLData(url)

        if data:
            html = BeautifulSoup(data, 'html.parser', parse_only = self.only_tables_tags)

            try:
                result_table = html.find('table', attrs = {'class': 'koptekst'})
                if not result_table or 'nothing found!' in data.lower():
                    return

                entries = result_table.find_all('tr')
                for result in entries[1:]:

                    all_cells = result.find_all('td')

                    torrent = all_cells[self.torrent_name_cell].find('a')
                    download = all_cells[self.torrent_download_cell].find('a')

                    torrent_id = torrent['href']
                    torrent_id = torrent_id.replace('details.php?id=', '')
                    torrent_id = torrent_id.replace('&hit=1', '')

                    torrent_name = torrent.getText()

                    torrent_size = self.parseSize(all_cells[8].getText())
                    torrent_seeders = tryInt(all_cells[10].getText())
                    torrent_leechers = tryInt(all_cells[11].getText())
                    torrent_url = self.urls['baseurl'] % download['href']
                    torrent_detail_url = self.urls['baseurl'] % torrent['href']

                    results.append({
                        'id': torrent_id,
                        'name': torrent_name,
                        'size': torrent_size,
                        'seeders': torrent_seeders,
                        'leechers': torrent_leechers,
                        'url': torrent_url,
                        'detail_url': torrent_detail_url,
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'ssl': 'yes',
        }

    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'bitsoup',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'Bitsoup',
            'description': '<a href="https://bitsoup.me">Bitsoup</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAB8ElEQVR4AbWSS2sTURiGz3euk0mswaE37HhNhIrajQheFgF3rgR/lAt/gOBCXNZlo6AbqfUWRVCxi04wqUnTRibpJLaJzdzOOZ6WUumyC5/VHOb9eN/FA91uFx0FjI4IPfgiGLTWH73tn348GKmN7ijD0d2b41fO5qJEaX24AWNIUrVQCTTJ3Llx6vbV6Vtzk7Gi9+ebi996guFDDYAQAVj4FExP5qdOZB49W62t/zH3hECcwsPnbWeMXz6Xi2K1f0ApeK3hMCHHbP5gvvoriBgFAAQJEAxhjJ4u+YWTNsVI6b1JgtPWZkoIefKy4fcii2OTw2BABs7wj3bYDlLL4rvjGWOdTser1j5Xf7c3Q/MbHQYApxItvnm31mhQQ71eX2vUB76/vsWB2hg0QuogrMwLIG8P3InM2/eVGXeDViqVwWB79vRU2lgJYmdHcgXCTAXQFJTN5HguvDCR2Hxsxe8EvT54nlcul5vNpqDIEgwRQanAhAAABgRIyiQcjpIkkTOuWyqVoN/vSylX67XXH74uV1vHRUyxxFqbLBCSmBpiXSq6xcL5QrGYzWZ3XQIAwdlOJB+/aL764ucdmncYs0WsCI7kvTnn+qyDMEnTVCn1Tz5KsBFg6fvWcmsUAcnYNC/g2hnromvvqbHvxv+39S+MX+bWkFXwAgAAAABJRU5ErkJggg==',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 20,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]

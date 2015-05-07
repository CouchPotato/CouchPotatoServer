import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://www.sceneaccess.eu/',
        'login': 'https://www.sceneaccess.eu/login',
        'login_check': 'https://www.sceneaccess.eu/inbox',
        'detail': 'https://www.sceneaccess.eu/details?id=%s',
        'search': 'https://www.sceneaccess.eu/browse?c%d=%d',
        'archive': 'https://www.sceneaccess.eu/archive?&c%d=%d',
        'download': 'https://www.sceneaccess.eu/%s',
    }

    http_time_between_calls = 1  # Seconds

    def _searchOnTitle(self, title, media, quality, results):

        url = self.buildUrl(title, media, quality)
        data = self.getHTMLData(url)

        if data:
            html = BeautifulSoup(data)

            try:
                resultsTable = html.find('table', attrs = {'id': 'torrents-table'})
                if resultsTable is None:
                    return

                entries = resultsTable.find_all('tr', attrs = {'class': 'tt_row'})
                for result in entries:

                    link = result.find('td', attrs = {'class': 'ttr_name'}).find('a')
                    url = result.find('td', attrs = {'class': 'td_dl'}).find('a')
                    seeders = result.find('td', attrs = {'class': 'ttr_seeders'}).find('a')
                    leechers = result.find('td', attrs = {'class': 'ttr_leechers'}).find('a')
                    torrent_id = link['href'].replace('details?id=', '')

                    results.append({
                        'id': torrent_id,
                        'name': link['title'],
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['detail'] % torrent_id,
                        'size': self.parseSize(result.find('td', attrs = {'class': 'ttr_size'}).contents[0]),
                        'seeders': tryInt(seeders.string) if seeders else 0,
                        'leechers': tryInt(leechers.string) if leechers else 0,
                        'get_more_info': self.getMoreInfo,
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getMoreInfo(self, item):
        full_description = self.getCache('sceneaccess.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('div', attrs = {'id': 'details_table'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

    # Login
    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'submit': 'come on in',
        }

    def loginSuccess(self, output):
        return '/inbox' in output.lower()

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'sceneaccess',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'SceneAccess',
            'description': '<a href="https://sceneaccess.eu/">SceneAccess</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAABnRSTlMAAAAAAABupgeRAAACT0lEQVR4AYVQS0sbURidO3OTmajJ5FElTTOkPmZ01GhHrIq0aoWAj1Vc+A/cuRMXbl24V9SlCGqrLhVFCrooEhCp2BAx0mobTY2kaR7qmOm87EXL1EWxh29xL+c7nPMdgGHYO5bF/gdbefnr6WlbWRnxluMwAB4Z0uEgXa7nwaDL7+/RNPzxbYvb/XJ0FBYVfd/ayh0fQ4qCGEHcm0KLRZUk7Pb2YRJPRwcsKMidnKD3t9VVT3s7BDh+z5FOZ3Vfn3h+Hltfx00mRRSRWFcUmmVNhYVqPn8dj3va2oh+txvcQRVF9ebm1fi4k+dRFbosY5rm4Hk7xxULQnJnx93S4g0EIEEQRoDLo6PrWEw8Pc0eHLwYGopMTDirqlJ7eyhYYGHhfgfHCcKYksZGVB/NcXI2mw6HhZERqrjYTNPHi4tFPh8aJIYIhgPlcCRDoZLW1s75+Z/7+59nZ/OJhLWigqAoKZX6Mjf3dXkZ3pydGYLc4aEoCCkInzQ1fRobS2xuvllaonkedfArnY5OTdGVldBkOADgqq2Nr6z8CIWaJietDHOhKB+HhwFKC6Gnq4ukKJvP9zcSbjYDXbeVlkKzuZBhnnV3e3t6UOmaJO0ODibW1hB1GYkg8R/gup7Z3TVZLJ5AILW9LcZiVpYtYBhw16O3t7cauckyeF9Tgz0ATpL2+nopmWycmbnY2LiKRjFk6/d7+/vRJfl4HGzV1T0UIM43MGBvaIBWK/YvwM5w+IMgGH8tkyEgvIpE7M3Nt6qqZrNyOq1kMmouh455Ggz+BhKY4GEc2CfwAAAAAElFTkSuQmCC',
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

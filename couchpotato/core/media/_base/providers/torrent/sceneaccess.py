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
                    leechers = result.find('td', attrs = {'class': 'ttr_leechers'}).find('a')
                    torrent_id = link['href'].replace('details?id=', '')

                    results.append({
                        'id': torrent_id,
                        'name': link['title'],
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['detail'] % torrent_id,
                        'size': self.parseSize(result.find('td', attrs = {'class': 'ttr_size'}).contents[0]),
                        'seeders': tryInt(result.find('td', attrs = {'class': 'ttr_seeders'}).find('a').string),
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
            'description': 'See <a href="https://sceneaccess.eu/">SceneAccess</a>',
            'wizard': True,
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

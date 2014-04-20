import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
import six


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://torrentshack.net/',
        'login': 'https://torrentshack.net/login.php',
        'login_check': 'https://torrentshack.net/inbox.php',
        'detail': 'https://torrentshack.net/torrent/%s',
        'search': 'https://torrentshack.net/torrents.php?action=advanced&searchstr=%s&scene=%s&filter_cat[%d]=1',
        'download': 'https://torrentshack.net/%s',
    }

    http_time_between_calls = 1  # Seconds

    def _search(self, media, quality, results):

        url = self.urls['search'] % self.buildUrl(media, quality)
        data = self.getHTMLData(url)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'id': 'torrent_table'})
                if not result_table:
                    return

                entries = result_table.find_all('tr', attrs = {'class': 'torrent'})

                for result in entries:

                    link = result.find('span', attrs = {'class': 'torrent_name_link'}).parent
                    url = result.find('td', attrs = {'class': 'torrent_td'}).find('a')

                    results.append({
                        'id': link['href'].replace('torrents.php?torrentid=', ''),
                        'name': six.text_type(link.span.string).translate({ord(six.u('\xad')): None}),
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['download'] % link['href'],
                        'size': self.parseSize(result.find_all('td')[4].string),
                        'seeders': tryInt(result.find_all('td')[6].string),
                        'leechers': tryInt(result.find_all('td')[7].string),
                    })

            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'keeplogged': '1',
            'login': 'Login',
        }

    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess

    def getSceneOnly(self):
        return '1' if self.conf('scene_only') else ''


config = [{
    'name': 'torrentshack',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'TorrentShack',
            'description': 'See <a href="https://www.torrentshack.net/">TorrentShack</a>',
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
                    'name': 'scene_only',
                    'type': 'bool',
                    'default': False,
                    'description': 'Only allow scene releases.'
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]

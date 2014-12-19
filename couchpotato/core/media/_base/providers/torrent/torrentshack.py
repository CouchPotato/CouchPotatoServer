import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
import six


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'http://torrentshack.eu/',
        'login': 'http://torrentshack.eu/login.php',
        'login_check': 'http://torrentshack.eu/inbox.php',
        'detail': 'http://torrentshack.eu/torrent/%s',
        'search': 'http://torrentshack.eu/torrents.php?action=advanced&searchstr=%s&scene=%s&filter_cat[%d]=1',
        'download': 'http://torrentshack.eu/%s',
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
                    size = result.find('td', attrs = {'class': 'size'}).contents[0].strip('\n ')
                    tds = result.find_all('td')

                    results.append({
                        'id': link['href'].replace('torrents.php?torrentid=', ''),
                        'name': six.text_type(link.span.string).translate({ord(six.u('\xad')): None}),
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['download'] % link['href'],
                        'size': self.parseSize(size),
                        'seeders': tryInt(tds[len(tds)-2].string),
                        'leechers': tryInt(tds[len(tds)-1].string),
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
            'description': '<a href="http://torrentshack.eu/">TorrentShack</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAABmElEQVQoFQXBzY2cVRiE0afqvd84CQiAnxWWtyxsS6ThINBYg2Dc7mZBMEjE4mzs6e9WcY5+ePNuVFJJodQAoLo+SaWCy9rcV8cmjah3CI6iYu7oRU30kE5xxELRfamklY3k1NL19sSm7vPzP/ZdNZzKVDaY2sPZJBh9fv5ITrmG2+Vp4e1sPchVqTCQZJnVXi+/L4uuAJGly1+Pw8CprLbi8Om7tbT19/XRqJUk11JP9uHj9ulxhXbvJbI9qJvr5YkGXFG2IBT8tXczt+sfzDZCp3765f3t9tHEHGEDACma77+8o4oATKk+/PfW9YmHruRFjWoVSFsVsGu1YSKq6Oc37+n98unPZSRlY7vsKDqN+92X3yR9+PdXee3iJNKMStqdcZqoTJbUSi5JOkpfRlhSI0mSpEmCFKoU7FqSNOLAk54uGwCStMUCgLrVic62g7oDoFmmdI+P3S0pDe1xvDqb6XrZqbtzShWNoh9fv/XQHaDdM9OqrZi2M7M3UrB2vlkPS1IbdEBk7UiSoD6VlZ6aKWer4aH4f/AvKoHUTjuyAAAAAElFTkSuQmCC',
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

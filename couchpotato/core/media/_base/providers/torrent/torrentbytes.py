import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://www.torrentbytes.net/',
        'login': 'https://www.torrentbytes.net/takelogin.php',
        'login_check': 'https://www.torrentbytes.net/inbox.php',
        'detail': 'https://www.torrentbytes.net/details.php?id=%s',
        'search': 'https://www.torrentbytes.net/browse.php?search=%s&cat=%d',
        'download': 'https://www.torrentbytes.net/download.php?id=%s&name=%s',
    }

    cat_ids = [
        ([5], ['720p', '1080p', 'bd50']),
        ([19], ['cam']),
        ([19], ['ts', 'tc']),
        ([19], ['r5', 'scr']),
        ([19], ['dvdrip']),
        ([19], ['brrip']),
        ([20], ['dvdr']),
    ]

    http_time_between_calls = 1  # Seconds
    cat_backup_id = None

    def _searchOnTitle(self, title, movie, quality, results):

        url = self.urls['search'] % (tryUrlencode('%s %s' % (title.replace(':', ''), movie['info']['year'])), self.getCatId(quality)[0])
        data = self.getHTMLData(url)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'border': '1'})
                if not result_table:
                    return

                entries = result_table.find_all('tr')

                for result in entries[1:]:
                    cells = result.find_all('td')

                    link = cells[1].find('a', attrs = {'class': 'index'})

                    full_id = link['href'].replace('details.php?id=', '')
                    torrent_id = full_id[:6]

                    results.append({
                        'id': torrent_id,
                        'name': link.contents[0],
                        'url': self.urls['download'] % (torrent_id, link.contents[0]),
                        'detail_url': self.urls['detail'] % torrent_id,
                        'size': self.parseSize(cells[6].contents[0] + cells[6].contents[2]),
                        'seeders': tryInt(cells[8].find('span').contents[0]),
                        'leechers': tryInt(cells[9].find('span').contents[0]),
                    })

            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'login': 'submit',
        }

    def loginSuccess(self, output):
        return 'logout.php' in output.lower() or 'Welcome' in output.lower()

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'torrentbytes',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'TorrentBytes',
            'description': '<a href="http://torrentbytes.net">TorrentBytes</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAeFBMVEUAAAAAAEQAA1QAEmEAKnQALHYAMoEAOokAQpIASYsASZgAS5UATZwATosATpgAVJ0AWZwAYZ4AZKAAaZ8Ab7IAcbMAfccAgcQAgcsAhM4AiscAjMkAmt0AoOIApecAp/EAqvQAs+kAt+wA3P8A4f8A//8VAAAfDbiaAl08AAAAjUlEQVQYGQXBO04DQRAFwHqz7Z8sECIl5f73ISRD5GBs7UxTlWfg9vYXnvJRQJqOL88D6BAwJtMMumHUVCl60aa6H93IrIv0b+157f1lpk+fm87lMWrZH0vncKbXdRUQrRmrh9C6Iwkq6rg4PXZcyXmbizzeV/g+rDra0rGve8jPKLSOJNi2AQAwAGjwD7ApPkEHdtPQAAAAAElFTkSuQmCC',
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

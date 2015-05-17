import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://www.scenetime.com/',
        'login': 'https://www.scenetime.com/takelogin.php',
        'login_check': 'https://www.scenetime.com/inbox.php',
        'detail': 'https://www.scenetime.com/details.php?id=%s',
        'search': 'https://www.scenetime.com/browse.php?search=%s&cat=%d',
        'download': 'https://www.scenetime.com/download.php/%s/%s',
    }

    cat_ids = [
        ([59], ['720p', '1080p']),
        ([81], ['brrip']),
        ([102], ['bd50']),
        ([3], ['dvdrip']),
    ]

    http_time_between_calls = 1  # Seconds
    cat_backup_id = None

    def _searchOnTitle(self, title, movie, quality, results):

        url = self.urls['search'] % (tryUrlencode('%s %s' % (title.replace(':', ''), movie['info']['year'])), self.getCatId(quality)[0])
        data = self.getHTMLData(url)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find(attrs = {'id': 'torrenttable'})

                if not result_table:
                    log.error('failed to generate result_table')
                    return

                entries = result_table.find_all('tr')
                
                for result in entries[1:]:
                    cells = result.find_all('td')
		    link = result.find('a', attrs = {'class': 'index'})
		    torrent_id = link['href'].replace('download.php/','').split('/')[0]
		    torrent_file = link['href'].replace('download.php/','').split('/')[1]
		    size = self.parseSize(cells[5].contents[0] + cells[5].contents[2])
		    name_row = cells[1].contents[0]
		    name = name_row.getText()
		    seeders_row = cells[6].contents[0]
		    seeders = seeders_row.getText()		     
		    
		    
                    results.append({
                        'id': torrent_id,
                        'name': name,
                        'url': self.urls['download']  % (torrent_id,torrent_file),
                        'detail_url': self.urls['detail'] % torrent_id,
                        'size': size,
                        'seeders': seeders,
                    })		    

            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return {
            'login': 'submit',
            'username': self.conf('username'),
            'password': self.conf('password'),
        }

    def loginSuccess(self, output):
        return 'logout.php' in output.lower() or 'Welcome' in output.lower()

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'scenetime',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'SceneTime',
            'description': '<a href="https://www.scenetime.com">SceneTime</a>',
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

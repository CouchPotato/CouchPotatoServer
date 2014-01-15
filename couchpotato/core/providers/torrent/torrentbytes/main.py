from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class TorrentBytes(TorrentProvider):

    urls = {
        'test' : 'https://www.torrentbytes.net/',
        'login' : 'https://www.torrentbytes.net/takelogin.php',
        'login_check' : 'https://www.torrentbytes.net/inbox.php',
        'detail' : 'https://www.torrentbytes.net/details.php?id=%s',
        'search' : 'https://www.torrentbytes.net/browse.php?search=%s&cat=%d',
        'download' : 'https://www.torrentbytes.net/download.php?id=%s&name=%s',
    }

    cat_ids = [
        ([5], ['720p', '1080p']),
        ([19], ['cam']),
        ([19], ['ts', 'tc']),
        ([19], ['r5', 'scr']),
        ([19], ['dvdrip']),
        ([5], ['brrip']),
        ([20], ['dvdr']),
    ]

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def _searchOnTitle(self, title, movie, quality, results):

        url = self.urls['search'] % (tryUrlencode('%s %s' % (title.replace(':', ''), movie['library']['year'])), self.getCatId(quality['identifier'])[0])
        data = self.getHTMLData(url)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'border' : '1'})
                if not result_table:
                    return

                entries = result_table.find_all('tr')

                for result in entries[1:]:
                    cells = result.find_all('td')

                    link = cells[1].find('a', attrs = {'class' : 'index'})

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


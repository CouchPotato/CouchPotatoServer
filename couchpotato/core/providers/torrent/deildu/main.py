from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class Deildu(TorrentProvider):

    urls = {
        'test': 'http://deildu.net/',
        'login' : 'http://deildu.net/takelogin.php',
        'detail': 'http://deildu.net/details.php?id=%s',
        'search': 'http://deildu.net/browse.php?sort=seeders&type=desc&cat=0',
        'base': 'http://deildu.net/',
    }

    http_time_between_calls = 5 #seconds

    def _searchOnTitle(self, title, movie, quality, results):

        q = '%s %s' % (simplifyString(title), movie['library']['year'])
        arguments = tryUrlencode({
            'search': q,
        })
        url = "%s&%s" % (self.urls['search'], arguments)

        # Cookie login
        if not self.login_opener and not self.login():
            return

        data = self.getHTMLData(url, opener = self.login_opener)

        # If nothing found, exit
        if 'Ekkert fannst!' in data:
            log.info("Deildu.net reported torrent not found: %s", q)
            return

        if data:
            html = BeautifulSoup(data)

            try:
                resultsTable = html.find('table', {'class': 'torrentlist'})
                entries = resultsTable.find_all('tr')
                for result in entries[1:]:

                    all_cells = result.find_all('td')

                    detail_link = all_cells[1].find('a')
                    details = detail_link['href']
                    torrent_id = details.replace('details.php?id=', '')
                    torrent_id = details.replace('&hit=1', '')

                    results.append({
                        'id': torrent_id,
                        'name': detail_link.get_text().strip(),
                        'size': self.parseSize(all_cells[6].get_text()),
                        'seeders': tryInt(all_cells[8].get_text()),
                        'leechers': tryInt(all_cells[9].get_text()),
                        'url': self.urls['base'] + all_cells[2].find('a')['href'],
                        'download': self.loginDownload,
                        'description': self.urls['base'] + all_cells[1].find('a')['href'],
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))


    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
        })

    def loginSuccess(self, output):
        return 'Login failed!' not in output

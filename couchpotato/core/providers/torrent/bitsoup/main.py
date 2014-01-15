from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class Bitsoup(TorrentProvider):

    urls = {
        'test': 'https://www.bitsoup.me/',
        'login' : 'https://www.bitsoup.me/takelogin.php',
        'login_check': 'https://www.bitsoup.me/my.php',
        'search': 'https://www.bitsoup.me/browse.php?',
        'baseurl': 'https://www.bitsoup.me/%s',
    }

    http_time_between_calls = 1 #seconds

    def _searchOnTitle(self, title, movie, quality, results):

        q = '"%s" %s' % (simplifyString(title), movie['library']['year'])
        arguments = tryUrlencode({
            'search': q,
        })
        url = "%s&%s" % (self.urls['search'], arguments)

        data = self.getHTMLData(url)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'class': 'koptekst'})
                if not result_table or 'nothing found!' in data.lower():
                    return

                entries = result_table.find_all('tr')
                for result in entries[1:]:

                    all_cells = result.find_all('td')

                    torrent = all_cells[1].find('a')
                    download = all_cells[3].find('a')

                    torrent_id = torrent['href']
                    torrent_id = torrent_id.replace('details.php?id=', '')
                    torrent_id = torrent_id.replace('&hit=1', '')

                    torrent_name = torrent.getText()

                    torrent_size = self.parseSize(all_cells[7].getText())
                    torrent_seeders = tryInt(all_cells[9].getText())
                    torrent_leechers = tryInt(all_cells[10].getText())
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


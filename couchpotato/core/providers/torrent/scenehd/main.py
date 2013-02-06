from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class SceneHD(TorrentProvider):

    urls = {
        'test': 'https://scenehd.org/',
        'login' : 'https://scenehd.org/takelogin.php',
        'detail': 'https://scenehd.org/details.php?id=%s',
        'search': 'https://scenehd.org/browse.php?ajax',
        'download': 'https://scenehd.org/download.php?id=%s',
    }

    http_time_between_calls = 1 #seconds

    def _searchOnTitle(self, title, movie, quality, results):

        q = '"%s %s"' % (simplifyString(title), movie['library']['year'])
        arguments = tryUrlencode({
            'search': q,
        })
        url = "%s&%s" % (self.urls['search'], arguments)

        # Cookie login
        if not self.login_opener and not self.login():
            return

        data = self.getHTMLData(url, opener = self.login_opener)

        if data:
            html = BeautifulSoup(data)

            try:
                resultsTable = html.find_all('table')[6]
                entries = resultsTable.find_all('tr')
                for result in entries[1:]:

                    all_cells = result.find_all('td')

                    detail_link = all_cells[2].find('a')
                    details = detail_link['href']
                    torrent_id = details.replace('details.php?id=', '')

                    leechers = all_cells[11].find('a')
                    if leechers:
                        leechers = leechers.string
                    else:
                        leechers = all_cells[11].string

                    results.append({
                        'id': torrent_id,
                        'name': detail_link['title'],
                        'size': self.parseSize(all_cells[7].string),
                        'seeders': tryInt(all_cells[10].find('a').string),
                        'leechers': tryInt(leechers),
                        'url': self.urls['download'] % torrent_id,
                        'download': self.loginDownload,
                        'description': all_cells[1].find('a')['href'],
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))


    def getLoginParams(self, params):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'ssl': 'yes',
        })

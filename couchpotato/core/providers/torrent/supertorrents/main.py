from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback


log = CPLog(__name__)

class SuperTorrents(TorrentProvider):
  
    urls = {
        'test' : 'http://www.supertorrents.com/',
        'base_url' : 'http://www.supertorrents.com',
        'login' : 'http://www.supertorrents.com/login.php',
        'search' : 'http://www.supertorrents.com/torrents/?c%d=1&incldead=0&search=%s',
        'download' : 'http://www.supertorrents.com/download.php/%s',
    }

    cat_ids = [
        ([9], ['DVDR']),
        ([13], ['BluRay','720p','1080p','DVDRIP']), #'BluRay 720p' & 'BluRay 1080p' 
        ([8], ['DVDrip','cam','ts','r5']),
    ]

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def _search(self, movie, quality, results):
      url = self.urls['search'] % (tryUrlencode('%s %s' % (title.replace(':', ''), movie['library']['year'])), self.getCatId(quality['identifier'])[0])
      data = self.getHTMLData(url, opener = self.login_opener)

      if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'class' : 'wishlist'})
                if not result_table:
                    return

                entries = result_table.find_all('tr')

                for result in entries[1:]:

                    link = result.find('td').find('a',attrs = {'class' : 'bigBold'}) #link = result.find('td', attrs = {'class' : 'bigBold'}).find('a')
                    url = result.find('td')[2].find('a')
                    details = result.find('td').find('a',attrs = {'class' : 'bigBold'})

                    results.append({
                        'id': link['href'].replace('/torrent/', ''),
                        'name': link.string,
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['download'] % details['href'],
                        'download': self.loginDownload,
                        'size': self.parseSize(result.find_all('td')[4].string),
                        'seeders': tryInt(result.find('td')[7].find_all('span').string),
                        'leechers': tryInt(result.find('td'[8].find_all('span').string)),
                    })

            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))



    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'remember_me': 'on',
            'login': 'Log in!',
        })

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback


log = CPLog(__name__)


class NextGenDev(TorrentProvider):

    loginUrl = ''
    
    def __init__(self):
        data_login = self.getHTMLData('https://nxtgn.org/login.php')
        bs = BeautifulSoup(data_login)
        csrfraw = bs.find('form', attrs = {'name': 'loginbox'})['action']
        login = 'https://nxtgn.org/' + csrfraw
        
        self.loginUrl = login
    
        
        
    urls = {
        'test' : 'https://www.nxtgn.org',
        'login_page': 'https://nxtgn.org/login.php',
        'login': loginUrl,
        'login_check': 'https://nxtgn.org/index.php',
        'detail' : 'https://nxtgn.org/details.php?id=%s',
        'search' : 'https://nxtgn.org/browse.php?search=%s',
        'download' : 'https://nxtgn.org/download.php?id=%s',
    }

    cat_ids = [
        ([13], ['720p', '1080p']),
        ([8], ['cam']),
        ([9], ['ts', 'tc']),
        ([10], ['r5', 'scr']),
        ([11], ['dvdrip']),
        ([14], ['brrip']),
        ([12], ['dvdr']),
    ]

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def _searchOnTitle(self, title, movie, quality, results):

        url = self.urls['search'] % (tryUrlencode('%s %s' % (title.replace(':', ''), movie['library']['year'])), self.getCatId(quality['identifier'])[0])
        data = self.getHTMLData(url, opener = self.login_opener)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'class' : 'torrents'})
                if not result_table:
                    return

                entries = result_table.find_all('tr')

                for result in entries[1:]:

                    link = result.find('td', attrs = {'class' : 'torrent-border'}).find('a')
                    url = result.find('a', attrs = {'class' : 'index'}).find('href')
                    details = result.find('td', attrs = {'class' : 'torrent-border'}).find('a')

                    results.append({
                        'id': link['href'].replace('download.php?id=', ''),
                        'name': link.string,
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['download'] % details['href'],
                        'size': self.parseSize(result.find_all('td')[8].string),
                        'seeders': tryInt(result.find_all('td')[9].string),
                        'leechers': tryInt(result.find_all('td')[10].string),
                    })

            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):


        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
        })

    def loginSuccess(self, output):
        return '/logout.php' in output.lower()

    loginCheckSuccess = loginSuccess
    

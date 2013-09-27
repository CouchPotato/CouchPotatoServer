from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback
import cookielib
import urllib2
import time

log = CPLog(__name__)


class NextGen(TorrentProvider):

    urls = {
        'test' : 'https://nxtgn.org/',
        'login_page' : 'https://nxtgn.org/login.php',
        'login' : 'https://nxtgn.org/takelogin.php',
        'detail' : 'https://nxtgn.org/details.php?id=%s',
        'search' : 'https://nxtgn.org/browse.php?search=%s&cat=0&incldead=0&modes=&c47=1&c17=1&c6=1&c16=1&c9=1&c12=1&c25=1&c38=1&c22=1&c28=1&c43=1&c33=1',
        'download' : 'https://nxtgn.org/download.php?id=%s',
    }

    http_time_between_calls = 1 #seconds

    cat_backup_id = None

    def _searchOnTitle(self, title, movie, quality, results):

        searchurl = self.urls['search'] % (tryUrlencode('%s %s' %(title.replace(':', ''), movie['library']['year'])))
        data = self.getHTMLData(searchurl, opener = self.login_opener)
        
        tableStartIndex = data.find("<table cellspacing=0 cellpadding=5 class=\"torrents\"><tr>")
        tableData = data[(tableStartIndex-1):]

        if data:
            torrentTable = BeautifulSoup(tableData)

        try:
            result_table = torrentTable.find('table', attrs = {'class' : 'torrents'})
            if not result_table:
                return

            entries = result_table.find_all('tr')

            for result in entries[1:]:
                
                torrentId = ((((result.find('td', attrs = {'class' :'torrent-border'})).find('a'))['href']).replace('details.php?id=','')).replace('&hit=1','')
                torrentName = ((result.find('td', attrs = {'class' :'torrent-border'})).find('a'))['title']

                    
                results.append({
                    'id': torrentId,
                    'name': torrentName,
                    'url': (self.urls['download'] % torrentId).encode('utf8'),
                    'detail_url': (self.urls['detail'] % torrentId).encode('utf8'),
                    'size':self.parseSize(result.contents[15].text),
                    'seeders': tryInt(result.contents[17].text),
            })

        except:
            log.error('Failed to parsing %s: %s', (self.getName(),traceback.format_exc()))


    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
        })

    def loginSuccess(self, output):
        if "<title>.:: NextGen :: Login ::.</title>" in output:
            return False
        else:
            return True
        

    loginCheckSuccess = loginSuccess

    def login(self):

        # Check if we are still logged in every hour
        now = time.time()
        if self.login_opener and self.last_login_check < (now - 3600):
            try:
                output = self.urlopen(self.urls['test'], opener = self.login_opener)
                if self.loginCheckSuccess(output):
                    self.last_login_check = now
                    return True
                else:
                    self.login_opener = None
            except:
                self.login_opener = None

        if self.login_opener:
            return True

        try:
            # Find csrf for login
            cookiejar = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
            data_login = self.getHTMLData(self.urls['login_page'], opener = opener)
            bs = BeautifulSoup(data_login)
            csrfraw = bs.find('form', attrs = {'name': 'loginbox'})['action']
            
            # Create 'login' in self.urls
            self.urls['login'] = (self.urls['test'] + csrfraw).encode('utf8')
            output = self.urlopen(self.urls['login'], params = self.getLoginParams(), opener = opener)
            

            if self.loginSuccess(output):
                self.last_login_check = now
                self.login_opener = opener
                return True

            error = 'unknown'
        except:
            error = traceback.format_exc()

        self.login_opener = None
        log.error('Failed to login %s: %s', (self.getName(), error))
        return False

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback
import re

log = CPLog(__name__)


class TehConnection(TorrentProvider):

    urls = {
        'test': 'https://tehconnection.eu/',
        'login': 'https://tehconnection.eu/login.php',
        'login_check': 'https://tehconnection.eu/index.php',
        'detail': 'https://tehconnection.eu/details?id=%s',
        'search': 'https://tehconnection.eu/torrents.php?action=advanced&%s',
        'download': 'https://tehconnection.eu%s',
    }

    http_time_between_calls = 1 #seconds

    def _search(self, movie, quality, results):

        # need to try logging in before every search
        if not '/logout.php' in self.urlopen(self.urls['login'], data = self.getLoginParams()).lower():
            log.info('problems logging into tehconnection.eu')
            return []

        data = self.getHTMLData(self.urls['search'] % tryUrlencode({'torrentname': '%s' % movie['library']['identifier'],'order_by': 's3'}))
        if data:
            try:
                resultsTable = BeautifulSoup(data).find('table', attrs = {'id' : 'browse_torrent_table'})
                if resultsTable is None:
                    log.info('movie not found on TehConnection')
                    return []
                year = resultsTable.find('font', attrs = {'class' : 'subtext'}).find('a')
                title_div = resultsTable.find('div', attrs = {'class' : 'torrent_title'}).find('a')
                id = title_div['href'].replace('/torrents.php?id=', '')
                releases = resultsTable.find_all('tr', attrs = {'class' : "groupid_%s" % (id) })

                for result in releases:
                    log.info('teh connection found ' + re.sub("\s+" , " ",re.sub(r'<.*?>', '','%s (%s) %s' % (title_div.string, year.string, unicode(result.find_all('td')[1].find_all('a')[2])))))
                    results.append({
			            'leechers': result.find_all('td')[7].string, 
			            'seeders': result.find_all('td')[6].string, 
			            'name': re.sub("\s+" , " ",re.sub(r'<.*?>', '','%s (%s) %s' % (title_div.string, year.string, unicode(result.find_all('td')[1].find_all('a')[2])))), 
			            'url': self.urls['download'] % result.find('a', attrs = {'title' : 'Download'})['href'].replace('amp;',''), 
			            'detail_url': self.urls['download'] % result.find('a', attrs = {'title' : 'Download'})['href'].replace('amp;',''), 
			            'id': '%s %s' % (id,self.parseSize(result.find_all('td')[4].string)), 
			            'size': self.parseSize(result.find_all('td')[4].string)
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'submit': 'Log In!',
        }

    def loginSuccess(self, output):
        return True

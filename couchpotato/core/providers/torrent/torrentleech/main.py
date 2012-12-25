from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import ResultList
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback


log = CPLog(__name__)


class TorrentLeech(TorrentProvider):

    urls = {
        'test' : 'http://www.torrentleech.org/',
        'login' : 'http://www.torrentleech.org/user/account/login/',
        'detail' : 'http://www.torrentleech.org/torrent/%s',
        'search' : 'http://www.torrentleech.org/torrents/browse/index/query/%s/categories/%d',
        'download' : 'http://www.torrentleech.org%s',
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

    def search(self, movie, quality):

        if self.isDisabled():
            return []

        # Cookie login
        if not self.login_opener and not self.login():
            return []

        results = ResultList(self, movie, quality)

        url = self.urls['search'] % (tryUrlencode(getTitle(movie['library']).replace(':', '') + ' ' + quality['identifier']), self.getCatId(quality['identifier'])[0])
        data = self.getHTMLData(url, opener = self.login_opener)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'id' : 'torrenttable'})
                if not result_table:
                    return []

                entries = result_table.find_all('tr')

                for result in entries[1:]:

                    link = result.find('td', attrs = {'class' : 'name'}).find('a')
                    url = result.find('td', attrs = {'class' : 'quickdownload'}).find('a')
                    details = result.find('td', attrs = {'class' : 'name'}).find('a')

                    results.append({
                        'id': link['href'].replace('/torrent/', ''),
                        'name': link.string,
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['download'] % details['href'],
                        'download': self.loginDownload,
                        'size': self.parseSize(result.find_all('td')[4].string),
                        'seeders': tryInt(result.find('td', attrs = {'class' : 'seeders'}).string),
                        'leechers': tryInt(result.find('td', attrs = {'class' : 'leechers'}).string),
                    })

            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

        return results

    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'remember_me': 'on',
            'login': 'submit',
        })

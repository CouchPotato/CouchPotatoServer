from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
import traceback
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
import six

log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'http://www.torrentleech.org/',
        'login': 'http://www.torrentleech.org/user/account/login/',
        'login_check': 'http://torrentleech.org/user/messages',
        'detail': 'http://www.torrentleech.org/torrent/%s',
        'search': 'http://www.torrentleech.org/torrents/browse/index/query/%s/categories/%d',
        'download': 'http://www.torrentleech.org%s',
    }

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def _search(self, media, quality, results):

        url = self.urls['search'] % self.buildUrl(media, quality)

        data = self.getHTMLData(url)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'id' : 'torrenttable'})
                if not result_table:
                    return

                entries = result_table.find_all('tr')

                for result in entries[1:]:

                    link = result.find('td', attrs = {'class' : 'name'}).find('a')
                    url = result.find('td', attrs = {'class' : 'quickdownload'}).find('a')
                    details = result.find('td', attrs = {'class' : 'name'}).find('a')

                    results.append({
                        'id': link['href'].replace('/torrent/', ''),
                        'name': six.text_type(link.string),
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['download'] % details['href'],
                        'size': self.parseSize(result.find_all('td')[4].string),
                        'seeders': tryInt(result.find('td', attrs = {'class' : 'seeders'}).string),
                        'leechers': tryInt(result.find('td', attrs = {'class' : 'leechers'}).string),
                    })

            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'remember_me': 'on',
            'login': 'submit',
        }

    def loginSuccess(self, output):
        return '/user/account/logout' in output.lower() or 'welcome back' in output.lower()

    loginCheckSuccess = loginSuccess

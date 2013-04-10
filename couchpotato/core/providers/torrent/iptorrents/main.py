from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback


log = CPLog(__name__)


class IPTorrents(TorrentProvider):

    urls = {
        'test' : 'http://www.iptorrents.com/',
        'base_url' : 'http://www.iptorrents.com',
        'login' : 'http://www.iptorrents.com/torrents/',
        'search' : 'http://www.iptorrents.com/torrents/?l%d=1%s&q=%s&qf=ti',
    }

    cat_ids = [
        ([48], ['720p', '1080p', 'bd50']),
        ([72], ['cam', 'ts', 'tc', 'r5', 'scr']),
        ([7], ['dvdrip', 'brrip']),
        ([6], ['dvdr']),
    ]

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def _searchOnTitle(self, title, movie, quality, results):

        freeleech = '' if not self.conf('freeleech') else '&free=on'

        url = self.urls['search'] % (self.getCatId(quality['identifier'])[0], freeleech, tryUrlencode('%s %s' % (title.replace(':', ''), movie['library']['year'])))
        data = self.getHTMLData(url, opener = self.login_opener)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'class' : 'torrents'})

                if not result_table or 'nothing found!' in data.lower():
                    return

                entries = result_table.find_all('tr')

                for result in entries[1:]:

                    torrent = result.find_all('td')[1].find('a')

                    torrent_id = torrent['href'].replace('/details.php?id=', '')
                    torrent_name = torrent.string
                    torrent_download_url = self.urls['base_url'] + (result.find_all('td')[3].find('a'))['href'].replace(' ', '.')
                    torrent_details_url = self.urls['base_url'] + torrent['href']
                    torrent_size = self.parseSize(result.find_all('td')[5].string)
                    torrent_seeders = tryInt(result.find('td', attrs = {'class' : 'ac t_seeders'}).string)
                    torrent_leechers = tryInt(result.find('td', attrs = {'class' : 'ac t_leechers'}).string)

                    results.append({
                        'id': torrent_id,
                        'name': torrent_name,
                        'url': torrent_download_url,
                        'detail_url': torrent_details_url,
                        'download': self.loginDownload,
                        'size': torrent_size,
                        'seeders': torrent_seeders,
                        'leechers': torrent_leechers,
                    })

            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

    def loginSuccess(self, output):
        return 'don\'t have an account' not in output.lower()

    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'login': 'submit',
        })

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class TorrentShack(TorrentProvider):

    urls = {
        'test' : 'http://www.torrentshack.net/',
        'login' : 'http://www.torrentshack.net/login.php',
        'login_check': 'http://www.torrentshack.net/inbox.php',
        'detail' : 'http://www.torrentshack.net/torrent/%s',
        'search' : 'http://www.torrentshack.net/torrents.php?searchstr=%s&filter_cat[%d]=1',
        'download' : 'http://www.torrentshack.net/%s',
    }

    cat_ids = [
        ([970], ['bd50']),
        ([300], ['720p', '1080p']),
        ([350], ['dvdr']),
        ([400], ['brrip', 'dvdrip']),
    ]

    http_time_between_calls = 1 #seconds
    cat_backup_id = 400

    def _searchOnTitle(self, title, movie, quality, results):

        url = self.urls['search'] % (tryUrlencode('"%s" %s' % (title.replace(':', ''), movie['library']['year'])), self.getCatId(quality['identifier'])[0])
        data = self.getHTMLData(url, opener = self.login_opener)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'id' : 'torrent_table'})
                if not result_table:
                    return

                entries = result_table.find_all('tr', attrs = {'class' : 'torrent'})

                for result in entries:

                    link = result.find('span', attrs = {'class' : 'torrent_name_link'}).parent
                    url = result.find('td', attrs = {'class' : 'torrent_td'}).find('a')

                    extra_info = ''
                    if result.find('span', attrs = {'class' : 'torrent_extra_info'}):
                        extra_info = result.find('span', attrs = {'class' : 'torrent_extra_info'}).text

                    if not self.conf('scene_only') or extra_info != '[NotScene]':
                        results.append({
                            'id': link['href'].replace('torrents.php?torrentid=', ''),
                            'name': unicode(link.span.string).translate({ord(u'\xad'): None}),
                            'url': self.urls['download'] % url['href'],
                            'detail_url': self.urls['download'] % link['href'],
                            'size': self.parseSize(result.find_all('td')[4].string),
                            'seeders': tryInt(result.find_all('td')[6].string),
                            'leechers': tryInt(result.find_all('td')[7].string),
                        })
                    else:
                        log.info('Not adding release %s [NotScene]' % unicode(link.span.string).translate({ord(u'\xad'): None}))

            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'keeplogged': '1',
            'login': 'Login',
        })

    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess

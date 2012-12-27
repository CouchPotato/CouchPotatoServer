from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class SceneAccess(TorrentProvider):

    urls = {
        'test': 'https://www.sceneaccess.eu/',
        'login' : 'https://www.sceneaccess.eu/login',
        'detail': 'https://www.sceneaccess.eu/details?id=%s',
        'search': 'https://www.sceneaccess.eu/browse?method=2&c%d=%d',
        'download': 'https://www.sceneaccess.eu/%s',
    }

    cat_ids = [
        ([22], ['720p', '1080p']),
        ([7], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
        ([8], ['dvdr']),
    ]

    http_time_between_calls = 1 #seconds

    def _search(self, movie, quality, results):

        url = self.urls['search'] % (
           self.getCatId(quality['identifier'])[0],
           self.getCatId(quality['identifier'])[0]
        )

        arguments = tryUrlencode({
            'search': movie['library']['identifier'],
            'method': 1,
        })
        url = "%s&%s" % (url, arguments)

        # Do login for the cookies
        if not self.login_opener and not self.login():
            return

        data = self.getHTMLData(url, opener = self.login_opener)

        if data:
            html = BeautifulSoup(data)

            try:
                resultsTable = html.find('table', attrs = {'id' : 'torrents-table'})
                if resultsTable is None:
                    return

                entries = resultsTable.find_all('tr', attrs = {'class' : 'tt_row'})
                for result in entries:

                    link = result.find('td', attrs = {'class' : 'ttr_name'}).find('a')
                    url = result.find('td', attrs = {'class' : 'td_dl'}).find('a')
                    leechers = result.find('td', attrs = {'class' : 'ttr_leechers'}).find('a')
                    torrent_id = link['href'].replace('details?id=', '')

                    results.append({
                        'id': torrent_id,
                        'name': link['title'],
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['detail'] % torrent_id,
                        'size': self.parseSize(result.find('td', attrs = {'class' : 'ttr_size'}).contents[0]),
                        'seeders': tryInt(result.find('td', attrs = {'class' : 'ttr_seeders'}).find('a').string),
                        'leechers': tryInt(leechers.string) if leechers else 0,
                        'download': self.loginDownload,
                        'get_more_info': self.getMoreInfo,
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'submit': 'come on in',
        })

    def getMoreInfo(self, item):
        full_description = self.getCache('sceneaccess.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('div', attrs = {'id':'details_table'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

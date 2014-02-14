from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class BiTHDTV(TorrentProvider):

    urls = {
        'test': 'http://www.bit-hdtv.com/',
        'login': 'http://www.bit-hdtv.com/takelogin.php',
        'login_check': 'http://www.bit-hdtv.com/messages.php',
        'detail': 'http://www.bit-hdtv.com/details.php?id=%s',
        'search': 'http://www.bit-hdtv.com/torrents.php?',
    }

    # Searches for movies only - BiT-HDTV's subcategory and resolution search filters appear to be broken
    cat_id_movies = 7

    http_time_between_calls = 1 #seconds

    def _searchOnTitle(self, title, movie, quality, results):

        arguments = tryUrlencode({
            'search': '%s %s' % (title.replace(':', ''), movie['library']['year']),
            'cat': self.cat_id_movies
        })

        url = "%s&%s" % (self.urls['search'], arguments)

        data = self.getHTMLData(url)

        if data:
            # Remove BiT-HDTV's output garbage so outdated BS4 versions successfully parse the HTML
            split_data = data.partition('-->')
            if '## SELECT COUNT(' in split_data[0]:
                data = split_data[2]

            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'width' : '750', 'class' : ''})
                if result_table is None:
                    return

                entries = result_table.find_all('tr')
                for result in entries[1:]:

                    cells = result.find_all('td')
                    link = cells[2].find('a')
                    torrent_id = link['href'].replace('/details.php?id=', '')

                    results.append({
                        'id': torrent_id,
                        'name': link.contents[0].get_text(),
                        'url': cells[0].find('a')['href'],
                        'detail_url': self.urls['detail'] % torrent_id,
                        'size': self.parseSize(cells[6].get_text()),
                        'seeders': tryInt(cells[8].string),
                        'leechers': tryInt(cells[9].string),
                        'get_more_info': self.getMoreInfo,
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
        }

    def getMoreInfo(self, item):
        full_description = self.getCache('bithdtv.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('table', attrs = {'class':'detail'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess

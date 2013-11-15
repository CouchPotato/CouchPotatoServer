from datetime import datetime
from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class BiTHDTV(TorrentProvider):

    urls = {
        'test' : 'http://www.bit-hdtv.com/',
        'login' : 'http://www.bit-hdtv.com/takelogin.php',
        'detail' : 'http://www.bit-hdtv.com/details.php?id=%s',
        'search' : 'http://www.bit-hdtv.com/torrents.php?search=%s&cat=%s&sub=%s',
    }

    # Searches for movies only - BiT-HDTV's subcategory and resolution search filters appear to be broken
    cat_id_movies = 7
    cat_ids = [
        ([16], ['720p', '1080p', 'brrip']),
        ([17], ['cam', 'r5', 'scr', 'dvdrip', 'dvdr']),
        ([19], ['ts', 'tc']),
    ]

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def _searchOnTitle(self, title, movie, quality, results):

        url = self.urls['search'] % (tryUrlencode('%s %s' % (title.replace(':', ''), movie['library']['year'])), self.cat_id_movies, self.getCatId(quality['identifier'])[0])
        data = self.getHTMLData(url, opener = self.login_opener)

        if data:

            # Remove BiT-HDTV's output garbage so outdated BS4 versions successfully parse the HTML
            split_data = data.partition('-->')
            if '## SELECT COUNT(' in split_data[0]:
                data = split_data[2]

            html = BeautifulSoup(data)

            try:
		result_table = html.find('table', attrs = {'width' : '750', 'class' : ''})
		if not result_table:
                    return

		entries = result_table.find_all('tr')

                for result in entries[1:]:
                    cells = result.find_all('td')
                    link = cells[2].find('a')
                    torrent_id = link['href'].replace('/details.php?id=', '')
                    torrent_age = datetime.now() - datetime.strptime(cells[5].get_text(), '%Y-%m-%d %H:%M:%S')

                    results.append({
                        'id': torrent_id,
                        'name': link.contents[0].get_text(),
                        'url': cells[0].find('a')['href'],
                        'detail_url': self.urls['detail'] % torrent_id,
                        'size': self.parseSize(cells[6].get_text()),
                        'age': torrent_age.days,
                        'seeders': tryInt(cells[8].string),
                        'leechers': tryInt(cells[9].string),
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'login': 'submit',
        })

    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

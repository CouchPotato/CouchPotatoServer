import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'detail': 'https://www.bit-hdtv.com/details.php?id=%s',
        'search': 'https://www.bit-hdtv.com/torrents.php?',
        'download': 'https://www.bit-hdtv.com/download.php?id=%s',
    }

    # Searches for movies only - BiT-HDTV's subcategory and resolution search filters appear to be broken
    http_time_between_calls = 1  # Seconds
    login_fail_msg = 'Username or password incorrect.'

    def _search(self, media, quality, results):

        query = self.buildUrl(media, quality)

        url = "%s&%s" % (self.urls['search'], query)

        data = self.getHTMLData(url, headers = self.getRequestHeaders())

        if data:
            # Remove BiT-HDTV's output garbage so outdated BS4 versions successfully parse the HTML
            split_data = data.partition('-->')
            if '## SELECT COUNT(' in split_data[0]:
                data = split_data[2]

            html = BeautifulSoup(data, 'html.parser')

            try:
                result_tables = html.find_all('table', attrs = {'width': '800', 'class': ''})
                if result_tables is None:
                    return

                # Take first result
                result_table = result_tables[0]

                if result_table is None:
                    return

                entries = result_table.find_all('tr')
                for result in entries[1:]:

                    cells = result.find_all('td')
                    link = cells[2].find('a')
                    torrent_id = link['href'].split('id=')[1]

                    results.append({
                        'id': torrent_id,
                        'name': link.contents[0].get_text(),
                        'url': self.urls['download'] % torrent_id,
                        'detail_url': self.urls['detail'] % torrent_id,
                        'size': self.parseSize(cells[6].get_text()),
                        'seeders': tryInt(cells[8].string),
                        'leechers': tryInt(cells[9].string),
                        'get_more_info': self.getMoreInfo,
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getRequestHeaders(self):
        cookies = 'h_sl={};h_sp={};h_su={}'.format(self.conf('cookiesettingsl') or '', self.conf('cookiesettingsp') or '', self.conf('cookiesettingsu') or '')
        return {
            'Cookie': cookies
        }

    def getMoreInfo(self, item):
        full_description = self.getCache('bithdtv.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('table', attrs = {'class': 'detail'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

    def download(self, url = '', nzb_id = ''):
        try:
            return self.urlopen(url, headers=self.getRequestHeaders())
        except:
            log.error('Failed getting release from %s: %s', (self.getName(), traceback.format_exc()))

        return 'try_next'

config = [{
    'name': 'bithdtv',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'BiT-HDTV',
            'description': '<a href="https://bit-hdtv.com" target="_blank">BiT-HDTV</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAABnRSTlMAAAAAAABupgeRAAABMklEQVR4AZ3Qu0ojcQCF8W9MJcQbJNgEEQUbQVIqWgnaWfkIvoCgggixEAmIhRtY2GV3w7KwU61B0EYIxmiw0YCik84ipaCuc0nmP5dcjIUgOjqDvxf4OAdf9mnMLcUJyPyGSCP+YRdC+Kp8iagJKhuS+InYRhTGgDbeV2uEMand4ZRxizjXHQEimxhraAnUr73BNqQxMiNeV2SwcjTLEVtb4Zl10mXutvOWm2otw5Sxz6TGTbdd6ncuYvVLXAXrvM+ruyBpy1S3JLGDfUQ1O6jn5vTsrJXvqSt4UNfj6vxTRPxBHER5QeSirhLGk/5rWN+ffB1XZuxjnDy1q87m7TS+xOGA+Iv4gfkbaw+nOMXHDHnITGEk0VfRFnn4Po4vNYm6RGukmggR0L08+l+e4HMeASo/i6AJUjLgAAAAAElFTkSuQmCC',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'cookiesettingsl',
                    'label': 'Cookies (h_sl)',
                    'default': '',
                    'description': 'Cookie h_sl from session',
                },
                {
                    'name': 'cookiesettingsp',
                    'label': 'Cookies (h_sp)',
                    'default': '',
                    'description': 'Cookie h_sp from session',
                },
                {
                    'name': 'cookiesettingsu',
                    'label': 'Cookies (h_su)',
                    'default': '',
                    'description': 'Cookie h_su from session',
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 20,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]

import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://www.bit-hdtv.com/',
        'login': 'https://www.bit-hdtv.com/takelogin.php',
        'login_check': 'https://www.bit-hdtv.com/messages.php',
        'detail': 'https://www.bit-hdtv.com/details.php?id=%s',
        'search': 'https://www.bit-hdtv.com/torrents.php?',
    }

    # Searches for movies only - BiT-HDTV's subcategory and resolution search filters appear to be broken
    http_time_between_calls = 1  # Seconds

    def _search(self, media, quality, results):

        query = self.buildUrl(media, quality)

        url = "%s&%s" % (self.urls['search'], query)

        data = self.getHTMLData(url)

        if data:
            # Remove BiT-HDTV's output garbage so outdated BS4 versions successfully parse the HTML
            split_data = data.partition('-->')
            if '## SELECT COUNT(' in split_data[0]:
                data = split_data[2]

            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'width': '750', 'class': ''})
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
        nfo_pre = html.find('table', attrs = {'class': 'detail'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'bithdtv',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'BiT-HDTV',
            'description': '<a href="https://bit-hdtv.com">BiT-HDTV</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAABnRSTlMAAAAAAABupgeRAAABMklEQVR4AZ3Qu0ojcQCF8W9MJcQbJNgEEQUbQVIqWgnaWfkIvoCgggixEAmIhRtY2GV3w7KwU61B0EYIxmiw0YCik84ipaCuc0nmP5dcjIUgOjqDvxf4OAdf9mnMLcUJyPyGSCP+YRdC+Kp8iagJKhuS+InYRhTGgDbeV2uEMand4ZRxizjXHQEimxhraAnUr73BNqQxMiNeV2SwcjTLEVtb4Zl10mXutvOWm2otw5Sxz6TGTbdd6ncuYvVLXAXrvM+ruyBpy1S3JLGDfUQ1O6jn5vTsrJXvqSt4UNfj6vxTRPxBHER5QeSirhLGk/5rWN+ffB1XZuxjnDy1q87m7TS+xOGA+Iv4gfkbaw+nOMXHDHnITGEk0VfRFnn4Po4vNYm6RGukmggR0L08+l+e4HMeASo/i6AJUjLgAAAAAElFTkSuQmCC',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
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

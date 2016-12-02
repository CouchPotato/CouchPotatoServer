import re
import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentMagnetProvider
import six


log = CPLog(__name__)

class Base(TorrentMagnetProvider):

    urls = {
        'search': 'http://www.magnetdl.com/%s/%s/se/desc/%s/',
        'detail': 'http://www.magnetdl.com/%s'
    }

    http_time_between_calls = 1  # Seconds

    def _searchOnTitle(self, title, movie, quality, results):

        movieTitle = tryUrlencode('%s-%s' % (title.replace(':', '').replace(' ', '-'), movie['info']['year']))

        next_page = True
        current_page = 1
        max_page = self.conf('max_pages')
        while next_page and current_page <= max_page and not self.shuttingDown():

            next_page = False
            url = self.urls['search'] % (movieTitle[:1], movieTitle, current_page)
            data = self.getHTMLData(url)

            if data:
                html = BeautifulSoup(data)

                try:
                    result_table = html.find('table', attrs = {'class': 'download'})
                    if not result_table:
                        return

                    entries = result_table.find_all('tr')
                    for result in entries:

                        if result.find('td', attrs = {'class': 'n'}):
                            link = result.find('td', attrs = {'class': 'n'}).find('a')
                            url = result.find('td', attrs = {'class': 'm'}).find('a')
                            tds = result.find_all('td')
                            size = tds[5].contents[0].strip('\n ')
                            age = tds[2].contents[0].strip('\n ')

                            results.append({
                                'id': link['href'].split('/')[2],
                                'name': link['title'],
                                'url': url['href'],
                                'detail_url': self.urls['detail'] % link['href'],
                                'size': self.parseSize(size),
                                'age' : self.ageToDays(age),
                                'seeders': tryInt(tds[len(tds)-2].string),
                                'leechers': tryInt(tds[len(tds)-1].string),
                            })
                        elif result.find('td', attrs = {'id': 'pages'}):
                            page_td = result.find('td', attrs = {'id': 'pages'})
                            next_title = 'Downloads | Page %s' % (current_page + 1)
                            if page_td.find('a', attrs = {'title': next_title}):
                                next_page = True

                except:
                    log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

            current_page += 1

    def ageToDays(self, age_str):
        age = 0
        age_str = age_str.replace('&nbsp;', ' ')

        regex = '(\d*.?\d+).(sec|hour|day|week|month|year)+'
        matches = re.findall(regex, age_str)
        for match in matches:
            nr, size = match
            mult = 1
            if size == 'week':
                mult = 7
            elif size == 'month':
                mult = 30.5
            elif size == 'year':
                mult = 365

            age += tryInt(nr) * mult

        return tryInt(age)

config = [{
    'name': 'magnetdl',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'MagnetDL',
            'description': '<a href="http://www.magnetdl.com/" target="_blank">MagnetDL</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAhBJREFUOBGFU89rE0EYfbObpk2qbpqY0ItV1NarFy1CqIeeehF68p6bP1Dx4Mn/QEQ8aDWHnEW8CLZo0ZMopQQtHiyWoqAgCdGNaxP3x8zOOjPJDBUW+2D4vtnvfW/mfcwSDNFoNO6L9MJwu1Sr1S7qmo7/5dTr9aTX66klc920O6ZxMprAGEO73VZbmachjWMEKKXwPE/1yTwNaRwjkFt/i1dRpPqcjWZaP3LNtUhwsrLofHinyEagtLqChfy2alxf3UoVKL14hoXxL+AxR/P5pi9JRiAGAQsH3mWehjghWRaE4NyG5hgBJubOooGAzNOgOEEETkagOUZAKtK9bjDkcELMDSx9UgzE1KdgAQW3LDwGbF2TUeyziW2rOouoEBjACNAErcBnysZY5SB2SoVzQ44KXtFZzE1WVD3oi4MEXxaMAE+s5e6OmIOwcfzsLMQ0rj4oOucfTkxMyZjY1qNjc6dU3fViMQeyLAXMuO8VCidz+0ffz0wC+UNHYJ04ja2Xr9H/6WK8VMT0fBV8cw29b1/x6TsHjaPpS53f28bnShC05jMjB/6EOJMPu7B9D4fnqjhanUV5qgJ/4w36ovlzJ4Efxjcv//Ce/nMDuZG4WyzcHs1Y18v7Ejhj4qEIk4wDv8Sz6fQJQpbcuuZ2bwzYuyzoDzLeEXZAiPy1F8UqC58tofEkQ8jSFdf9KDkafwGzPw7miJh+wQAAAABJRU5ErkJggg==',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
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
                    'name': 'max_pages',
                    'label': 'Max Pages',
                    'type': 'int',
                    'default': 3,
                    'description': 'Maximum number of pages to scan.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]

import re
import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.torrent.base import TorrentMagnetProvider
from couchpotato.core.helpers.encoding import tryUrlencode


log = CPLog(__name__)


class Base(TorrentMagnetProvider):

    COLUMN_NAME = 0
    COLUMN_SIZE = 1
    COLUMN_FILES = 2 # Unused
    COLUMN_AGE = 3
    COLUMN_SEEDS = 4
    COLUMN_LEECHERS = 5

    MAX_PAGES = 2

    # The url for the first page containing search results is not postfixed
    # with a page number, but providing it is allowed.
    urls = {
        'detail': '%s/%%s',
        'search': '%s/usearch/%s/%d/',
    }

    cat_ids = [
        (['cam'], ['cam']),
        (['telesync'], ['ts', 'tc']),
        (['screener', 'tvrip'], ['screener']),
        (['x264', '720p', '1080p', 'blu-ray', 'hdrip'], ['bd50', '1080p', '720p', 'brrip']),
        (['dvdrip'], ['dvdrip']),
        (['dvd'], ['dvdr']),
        (['hdtv'], ['hdtv'])
    ]

    http_time_between_calls = 1  # Seconds
    cat_backup_id = None

    proxy_list = [
        'https://kat.cr',
        'https://kickass.unblocked.pw/',
        'https://katproxy.com',
    ]


    def _searchOnTitle(self, title, media, quality, results):
        # _searchOnTitle can be safely implemented here because the existence
        # of a _search method on the provider is checked first, in which case
        # the KickassTorrents movie provider searches for the movie using the
        # IMDB identifier as a key.

        cat_ids = self.getCatId(quality)

        base_detail_url = self.urls['detail'] % (self.getDomain())

        page = 1
        pages = 1
        referer_url = None
        while page <= pages and page <= self.MAX_PAGES:
            # The use of buildUrl might be required in the future to scan
            # multiple pages of show results.
            url = self.buildUrl(title = title, media = media, page = page)
            if url and referer_url and url == referer_url:
                break

            data = self.getHTMLData(url)

            try:
                html = BeautifulSoup(data)
                table = html.find('table', attrs = {'class': 'data'})
                for tr in table.find_all('tr', attrs={'class': ['odd', 'even']}):
                    try:
                        result = { }
                        column = 0
                        for td in tr.find_all('td'):
                            if column == self.COLUMN_NAME:
                                link = td.find('a', 'cellMainLink')
                                for tag in link.findAll(True):
                                    tag.unwrap()

                                result['id'] = tr['id'][-7:]
                                result['name'] = link.text
                                result['url'] = td.find('a', 'imagnet')['href']
                                result['detail_url'] = base_detail_url % (link['href'][1:])
                                if td.find('a', 'iverify'):
                                    result['verified'] = True
                                    result['score'] = 100
                                else:
                                    result['verified'] = False
                                    result['score'] = 0
                            elif column == self.COLUMN_SIZE:
                                result['size'] = self.parseSize(td.text)
                            elif column == self.COLUMN_AGE:
                                result['age'] = self.ageToDays(td.text)
                            elif column == self.COLUMN_SEEDS:
                                result['seeders'] = tryInt(td.text, 0)
                            elif column == self.COLUMN_LEECHERS:
                                result['leechers'] = tryInt(td.text, 0)

                            column += 1

                        if result:
                            # The name must at least contain one category identifier
                            score = 0
                            for cat_id in cat_ids:
                                if cat_id.lower() in result['name'].lower():
                                    score += 1
                                    break

                            if result['verified'] or not self.conf('only_verified'):
                                score += 1

                            if score == 2:
                                results.append(result)

                        buttons = html.find('div', 'pages')
                        if buttons:
                            pages = len(buttons.find_all(True, recursive = False))
                    except:
                        log.error('Failed parsing KickAssTorrents: %s', traceback.format_exc())

                page += 1
                referer_url = url

            except AttributeError:
                log.debug('No search results found.')

    def buildUrl(self, *args, **kwargs):
        # KickassTorrents also supports the "season:X episode:Y" parameters
        # which would arguably make the search more robust, but we cannot use
        # this mechanism because it might break searching for daily talk shows
        # and the like, e.g. Jimmy Fallon.
        media = kwargs.get('media', None)
        title = kwargs.get('title', None)
        page = kwargs.get('page', 1)
        if not title and media:
            title = fireEvent('library.query', media, single = True)
        if not title:
            return False
        assert isinstance(page, (int, long))

        return self.urls['search'] % (self.getDomain(), tryUrlencode(title), page)

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

    def isEnabled(self):
        return super(Base, self).isEnabled() and self.getDomain()

    def correctProxy(self, data):
        return 'search query' in data.lower()

config = [{
    'name': 'kickasstorrents',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'KickAssTorrents',
            'description': '<a href="https://kat.ph/">KickAssTorrents</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACD0lEQVR42pXK20uTcRjA8d/fsJsuap0orBuFlm3hir3JJvQOVmuwllN20Lb2isI2nVHKjBqrCWYaNnNuBrkSWxglhDVJOkBdSWUOq5FgoiOrMdRJ2xPPxW+8OUf1ge/FcyCUSVe2qedK5U/OxNTTXRNXEQ52Glb4O6dNEfK1auJkvRY7+/zxnQbA/D596laXcY3OWOiaIX2393SGznUmxkUo/YkDgqHemuzobQ7+NV+reo5Q1mqp68GABdY3+/EloO+JeN4tEqiFU8f3CwhyWo9E7wfMgI0ELTDx0AvjIxcgvZoC9P7NMN7yMmrFeoKa68rfDfmrARsNN0Ihr55cx59ctZWSiwS5bLKpwW4dYJH+M/B6/CYszE0BFZ+egG+Ln+HRoBN/cpl1pV6COIMkOnBVA/w+fXgGKJVM4LxhumMleoL06hJ3wKcCfl+/TAKKx17gnFePRwkqxR4BQSpFkbCrrQJueI7mWpyfATQ9OQY43+uv/+PutBycJ3y2qn2x7jY50GJvnwLKZjOwspyE5I8F4N+1yr1uwqcs3ym63Hwo29EiAyzUWQVr6WVAS4lZCPutQG/2GtES2YiW3d3XflYKtL72kzAcdEDHeSa3czeIMyyz/TApRKvcFfE0isHbJMnrHCf6xTLb1ORvWNlWo91cvHrJUQo0o6ZoRi7dIiT/g2WEDi27Iyov21xMCvgNfXvtwIACfHwAAAAASUVORK5CYII=',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True,
                },
                {
                    'name': 'domain',
                    'advanced': True,
                    'label': 'Proxy server',
                    'description': 'Domain for requests, keep empty to let CouchPotato pick.',
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
                    'name': 'only_verified',
                    'advanced': True,
                    'type': 'bool',
                    'default': False,
                    'description': 'Only search for verified releases.'
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

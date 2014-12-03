import re
import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentMagnetProvider


log = CPLog(__name__)


class Base(TorrentMagnetProvider):

    urls = {
        'detail': '%s/%s',
        'search': '%s/%s-i%s/',
    }

    cat_ids = [
        (['cam'], ['cam']),
        (['telesync'], ['ts', 'tc']),
        (['screener', 'tvrip'], ['screener']),
        (['x264', '720p', '1080p', 'blu-ray', 'hdrip'], ['bd50', '1080p', '720p', 'brrip']),
        (['dvdrip'], ['dvdrip']),
        (['dvd'], ['dvdr']),
    ]

    http_time_between_calls = 1  # Seconds
    cat_backup_id = None

    proxy_list = [
        'https://kickass.so',
        'http://kickass.pw',
        'http://kickassto.come.in',
        'http://katproxy.ws',
        'http://kickass.bitproxy.eu',
        'http://katph.eu',
        'http://kickassto.come.in',
    ]

    def _search(self, media, quality, results):

        data = self.getHTMLData(self.urls['search'] % (self.getDomain(), 'm', getIdentifier(media).replace('tt', '')))

        if data:

            cat_ids = self.getCatId(quality)
            table_order = ['name', 'size', None, 'age', 'seeds', 'leechers']

            try:
                html = BeautifulSoup(data)
                resultdiv = html.find('div', attrs = {'class': 'tabs'})
                for result in resultdiv.find_all('div', recursive = False):
                    if result.get('id').lower().strip('tab-') not in cat_ids:
                        continue

                    try:
                        for temp in result.find_all('tr'):
                            if temp['class'] is 'firstr' or not temp.get('id'):
                                continue

                            new = {}

                            nr = 0
                            for td in temp.find_all('td'):
                                column_name = table_order[nr]
                                if column_name:

                                    if column_name == 'name':
                                        link = td.find('div', {'class': 'torrentname'}).find_all('a')[2]
                                        new['id'] = temp.get('id')[-7:]
                                        new['name'] = link.text
                                        new['url'] = td.find('a', 'imagnet')['href']
                                        new['detail_url'] = self.urls['detail'] % (self.getDomain(), link['href'][1:])
                                        new['verified'] = True if td.find('a', 'iverify') else False
                                        new['score'] = 100 if new['verified'] else 0
                                    elif column_name is 'size':
                                        new['size'] = self.parseSize(td.text)
                                    elif column_name is 'age':
                                        new['age'] = self.ageToDays(td.text)
                                    elif column_name is 'seeds':
                                        new['seeders'] = tryInt(td.text)
                                    elif column_name is 'leechers':
                                        new['leechers'] = tryInt(td.text)

                                nr += 1

                            # Only store verified torrents
                            if self.conf('only_verified') and not new['verified']:
                                continue

                            results.append(new)
                    except:
                        log.error('Failed parsing KickAssTorrents: %s', traceback.format_exc())

            except AttributeError:
                log.debug('No search results found.')

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

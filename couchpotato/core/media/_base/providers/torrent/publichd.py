from urlparse import parse_qs
import re
import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentMagnetProvider
import six


log = CPLog(__name__)


class Base(TorrentMagnetProvider):

    urls = {
        'test': 'https://publichd.to',
        'detail': 'https://publichd.to/index.php?page=torrent-details&id=%s',
        'search': 'https://publichd.to/index.php',
    }
    http_time_between_calls = 0

    def search(self, movie, quality):

        if not quality.get('hd', False):
            return []

        return super(Base, self).search(movie, quality)

    def _search(self, media, quality, results):

        query = self.buildUrl(media)

        params = tryUrlencode({
            'page': 'torrents',
            'search': query,
            'active': 1,
        })

        data = self.getHTMLData('%s?%s' % (self.urls['search'], params))

        if data:

            try:
                soup = BeautifulSoup(data)

                results_table = soup.find('table', attrs = {'id': 'bgtorrlist2'})
                entries = results_table.find_all('tr')

                for result in entries[2:len(entries) - 1]:
                    info_url = result.find(href = re.compile('torrent-details'))
                    download = result.find(href = re.compile('magnet:'))

                    if info_url and download:

                        url = parse_qs(info_url['href'])

                        results.append({
                            'id': url['id'][0],
                            'name': six.text_type(info_url.string),
                            'url': download['href'],
                            'detail_url': self.urls['detail'] % url['id'][0],
                            'size': self.parseSize(result.find_all('td')[7].string),
                            'seeders': tryInt(result.find_all('td')[4].string),
                            'leechers': tryInt(result.find_all('td')[5].string),
                            'get_more_info': self.getMoreInfo
                        })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getMoreInfo(self, item):

        cache_key = 'publichd.%s' % item['id']
        description = self.getCache(cache_key)

        if not description:

            try:
                full_description = self.urlopen(item['detail_url'])
                html = BeautifulSoup(full_description)
                nfo_pre = html.find('div', attrs = {'id': 'torrmain'})
                description = toUnicode(nfo_pre.text) if nfo_pre else ''
            except:
                log.error('Failed getting more info for %s', item['name'])
                description = ''

            self.setCache(cache_key, description, timeout = 25920000)

        item['description'] = description
        return item


config = [{
    'name': 'publichd',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'PublicHD',
            'description': 'Public Torrent site with only HD content. See <a href="https://publichd.to/">PublicHD</a>',
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAASFJREFUOI3VkjtLxEAUhb87TNZgoSIoNqYUFUGw9Bdoo5UoItgoLrJFWsHa3sLav6GNoI2NxYqIDwQRC1+FLLgx2SQzFiNLLGyyjR6Y6t773XNmBv69BHgEVMl5I0AL8EoCUlWdE9O4Vt9mnLZW4OFWAOH9Bp5O4e28cOrwXIfaohi9VrP0xALYNuDjE4LAMjYAfT5c3CmOzhSedvVWJoSrKQtLFp1EQGrZ39Z0VcAYCAYtNHKiGNBweW8Id03BuRBWhbhpcUwDQ+M5WoGxbitpIZXwq7TvAxVhdtm2Y2zOw94MdPtABiPDws6GwvNcS5IKxBm+D/rgRJha/0nt74WoCVevDjk6aZmYzovXRJIJh8fOXEfPqIEXOvhIJef+kr4AxLZfW1OtpggAAAAASUVORK5CYII=',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True,
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
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]

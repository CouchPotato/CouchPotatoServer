import re
import traceback

from bs4 import BeautifulSoup
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentMagnetProvider
import six


log = CPLog(__name__)


class Base(TorrentMagnetProvider):

    urls = {
         'detail': '%s/torrent/%s',
         'search': '%s/search/%%s/%%s/7/%%s'
    }

    cat_backup_id = 200
    disable_provider = False
    http_time_between_calls = 0

    proxy_list = [
        'https://pirateproxy.cat',
        'https://pirateproxy.wf',
        'https://pirateproxy.tf',
        'https://urbanproxy.eu',
        'https://piratebays.co',
        'https://pirateproxy.yt',
        'https://thepiratebay.uk.net',
        'https://thebay.tv',
        'https://thepirateproxy.co',
        'https://theproxypirate.pw',
        'https://arrr.xyz',
        'https://tpb.dashitz.com'
    ]

    def __init__(self):
        super(Base, self).__init__()

        addEvent('app.test', self.doTest)

    def _search(self, media, quality, results):

        page = 0
        total_pages = 1
        cats = self.getCatId(quality)

        base_search_url = self.urls['search'] % self.getDomain()

        while page < total_pages:

            search_url = base_search_url % self.buildUrl(media, page, cats)

            page += 1

            data = self.getHTMLData(search_url)

            if data:
                try:
                    soup = BeautifulSoup(data)
                    results_table = soup.find('table', attrs = {'id': 'searchResult'})

                    if not results_table:
                        return

                    try:
                        total_pages = len(soup.find('div', attrs = {'align': 'center'}).find_all('a'))
                    except:
                        pass

                    entries = results_table.find_all('tr')
                    for result in entries[1:]:
                        link = result.find(href = re.compile('torrent\/\d+\/'))
                        download = result.find(href = re.compile('magnet:'))

                        try:
                            size = re.search('Size (?P<size>.+),', six.text_type(result.select('font.detDesc')[0])).group('size')
                        except:
                            continue

                        if link and download:
                            if self.conf('trusted_only'):
                                if result.find('img', alt = re.compile('Trusted')) is None and \
                                                result.find('img', alt = re.compile('VIP')) is None and \
                                                result.find('img', alt = re.compile('Helpers')) is None and \
                                                result.find('img', alt = re.compile('Moderator')) is None:
                                    log.info('Skipped torrent %s, untrusted.' % link.string)
                                    continue

                            def extra_score(item):
                                trusted = (0, 10)[result.find('img', alt = re.compile('Trusted')) is not None]
                                vip = (0, 20)[result.find('img', alt = re.compile('VIP')) is not None]
                                confirmed = (0, 30)[result.find('img', alt = re.compile('Helpers')) is not None]
                                moderated = (0, 50)[result.find('img', alt = re.compile('Moderator')) is not None]

                                return confirmed + trusted + vip + moderated

                            results.append({
                                'id': re.search('/(?P<id>\d+)/', link['href']).group('id'),
                                'name': six.text_type(link.string),
                                'url': download['href'],
                                'detail_url': self.getDomain(link['href']),
                                'size': self.parseSize(size),
                                'seeders': tryInt(result.find_all('td')[2].string),
                                'leechers': tryInt(result.find_all('td')[3].string),
                                'extra_score': extra_score,
                                'get_more_info': self.getMoreInfo
                            })

                except:
                    log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def isEnabled(self):
        return super(Base, self).isEnabled() and self.getDomain()

    def correctProxy(self, data):
        return 'title="Pirate Search"' in data

    def getMoreInfo(self, item):
        full_description = self.getCache('tpb.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('div', attrs = {'class': 'nfo'})
        description = ''
        try:
            description = toUnicode(nfo_pre.text)
        except:
            pass

        item['description'] = description
        return item

    def doTest(self):

        for url in self.proxy_list:
            try:
                data = self.urlopen(url + '/search/test+search')

                if 'value="test+search"' in data:
                    log.info('Success %s', url)
                    continue
            except:
                log.error('%s', traceback.format_exc(0))


config = [{
    'name': 'thepiratebay',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'ThePirateBay',
            'description': 'The world\'s largest bittorrent tracker. <a href="https://thepiratebay.se/" target="_blank">ThePirateBay</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAAAAAA6mKC9AAAA3UlEQVQY02P4DwT/YADIZvj//7qnozMYODmtAAusZoCDELDAegYGViZhAWZmRoYoqIDupfhNN1M3dTBEggXWMZg9jZRXV77YxhAOFpjDwMAPMoCXmcHsF1SAQZ6bQY2VgUEbKHClcAYzg3mINEO8jSCD478/DPsZmvqWblu1bOmStes3Pp0ezVDF4Gif0Hfx9///74/ObRZ2YNiZ47C8XIRBxFJR0jbSSUud4f9zAQWn8NTuziAt2zy5xIMM/z8LFX0E+fD/x0MRDCeA1v7Z++Y/FDzyvAtyBxIA+h8A8ZKLeT+lJroAAAAASUVORK5CYII=',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False
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
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                },
                {
                    'name': 'trusted_only',
                    'advanced': True,
                    'label': 'Trusted/VIP Only',
                    'type': 'bool',
                    'default': False,
                    'description': 'Only download releases marked as Trusted or VIP'
                }
            ],
        }
    ]
}]

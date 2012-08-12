from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getTitle, tryInt, cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
from couchpotato.environment import Env
from urllib import quote_plus
import re
import time
import traceback

log = CPLog(__name__)


class ThePirateBay(TorrentProvider):

    urls = {
         'detail': '%s/torrent/%s',
         'search': '%s/search/%s/0/7/%d'
    }

    cat_ids = [
       ([207], ['720p', '1080p']),
       ([201], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
       ([202], ['dvdr'])
    ]

    cat_backup_id = 200
    disable_provider = False
    http_time_between_calls = 0

    proxy_list = [
        'https://thepiratebay.se',
        'https://tpb.ipredator.se',
        'https://depiraatbaai.be',
        'https://piratereverse.info',
        'https://tpb.pirateparty.org.uk',
        'https://argumentomteemigreren.nl',
    ]

    def __init__(self):
        self.domain = self.conf('domain')
        super(ThePirateBay, self).__init__()

    def getDomain(self, url = ''):

        if not self.domain:
            for proxy in self.proxy_list:

                prop_name = 'tpb_proxy.%s' % proxy
                last_check = float(Env.prop(prop_name, default = 0))
                if last_check > time.time() - 1209600:
                    continue

                data = ''
                try:
                    data = self.urlopen(proxy, timeout = 3)
                except:
                    log.debug('Failed tpb proxy %s', proxy)

                if 'title="Pirate Search"' in data:
                    log.debug('Using proxy: %s', proxy)
                    self.domain = proxy
                    break

                Env.prop(prop_name, time.time())

        if not self.domain:
            log.error('No TPB proxies left, please add one in settings, or let us know which one to add on the forum.')
            return None

        return cleanHost(self.domain).rstrip('/') + url

    def search(self, movie, quality):

        results = []
        if self.isDisabled() or not self.getDomain():
            return results

        cache_key = 'thepiratebay.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
        search_url = self.urls['search'] % (self.getDomain(), quote_plus(getTitle(movie['library']) + ' ' + quality['identifier']), self.getCatId(quality['identifier'])[0])
        data = self.getCache(cache_key, search_url)

        if data:
            try:
                soup = BeautifulSoup(data)
                results_table = soup.find('table', attrs = {'id': 'searchResult'})
                entries = results_table.find_all('tr')
                for result in entries[1:]:
                    link = result.find(href = re.compile('torrent\/\d+\/'))
                    download = result.find(href = re.compile('magnet:'))

                    size = re.search('Size (?P<size>.+),', unicode(result.select('font.detDesc')[0])).group('size')
                    if link and download:

                        def extra_score(item):
                            trusted = (0, 10)[result.find('img', alt = re.compile('Trusted')) != None]
                            vip = (0, 20)[result.find('img', alt = re.compile('VIP')) != None]
                            confirmed = (0, 30)[result.find('img', alt = re.compile('Helpers')) != None]
                            moderated = (0, 50)[result.find('img', alt = re.compile('Moderator')) != None]

                            return confirmed + trusted + vip + moderated

                        new = {
                            'id': re.search('/(?P<id>\d+)/', link['href']).group('id'),
                            'type': 'torrent_magnet',
                            'name': link.string,
                            'check_nzb': False,
                            'description': '',
                            'provider': self.getName(),
                            'url': download['href'],
                            'detail_url': self.getDomain(link['href']),
                            'size': self.parseSize(size),
                            'seeders': tryInt(result.find_all('td')[2].string),
                            'leechers': tryInt(result.find_all('td')[3].string),
                            'extra_score': extra_score,
                            'get_more_info': self.getMoreInfo
                        }

                        new['score'] = fireEvent('score.calculate', new, movie, single = True)
                        is_correct_movie = fireEvent('searcher.correct_movie', nzb = new, movie = movie, quality = quality,
                                                        imdb_results = False, single = True)

                        if is_correct_movie:
                            results.append(new)
                            self.found(new)

                return results
            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

        return []

    def getMoreInfo(self, item):
        full_description = self.getCache('tpb.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('div', attrs = {'class':'nfo'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

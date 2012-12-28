from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.variable import tryInt, cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentMagnetProvider
from couchpotato.environment import Env
import re
import time
import traceback

log = CPLog(__name__)


class ThePirateBay(TorrentMagnetProvider):

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
        'https://livepirate.com/',
        'https://www.getpirate.com/',
    ]

    def __init__(self):
        self.domain = self.conf('domain')
        super(ThePirateBay, self).__init__()

    def _searchOnTitle(self, title, movie, quality, results):

        search_url = self.urls['search'] % (self.getDomain(), tryUrlencode(title + ' ' + quality['identifier']), self.getCatId(quality['identifier'])[0])

        data = self.getHTMLData(search_url)

        if data:
            try:
                soup = BeautifulSoup(data)
                results_table = soup.find('table', attrs = {'id': 'searchResult'})

                if not results_table:
                    return

                entries = results_table.find_all('tr')
                for result in entries[2:]:
                    link = result.find(href = re.compile('torrent\/\d+\/'))
                    download = result.find(href = re.compile('magnet:'))

                    try:
                        size = re.search('Size (?P<size>.+),', unicode(result.select('font.detDesc')[0])).group('size')
                    except:
                        continue

                    if link and download:

                        def extra_score(item):
                            trusted = (0, 10)[result.find('img', alt = re.compile('Trusted')) != None]
                            vip = (0, 20)[result.find('img', alt = re.compile('VIP')) != None]
                            confirmed = (0, 30)[result.find('img', alt = re.compile('Helpers')) != None]
                            moderated = (0, 50)[result.find('img', alt = re.compile('Moderator')) != None]

                            return confirmed + trusted + vip + moderated

                        results.append({
                            'id': re.search('/(?P<id>\d+)/', link['href']).group('id'),
                            'name': link.string,
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
        return super(ThePirateBay, self).isEnabled() and self.getDomain()

    def getDomain(self, url = ''):

        if not self.domain:
            for proxy in self.proxy_list:

                prop_name = 'tpb_proxy.%s' % proxy
                last_check = float(Env.prop(prop_name, default = 0))
                if last_check > time.time() - 1209600:
                    continue

                data = ''
                try:
                    data = self.urlopen(proxy, timeout = 3, show_error = False)
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

    def getMoreInfo(self, item):
        full_description = self.getCache('tpb.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('div', attrs = {'class':'nfo'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

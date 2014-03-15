from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentMagnetProvider
import re
import traceback
import six

log = CPLog(__name__)


class ThePirateBay(TorrentMagnetProvider):

    urls = {
        'detail': '%s/torrent/%s',
        'search': '%s/search/%s/%s/7/%s'
    }

    cat_ids = [
        ([207], ['720p', '1080p']),
        ([201], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr']),
        ([201, 207], ['brrip']),
        ([202], ['dvdr'])
    ]

    cat_backup_id = 200
    disable_provider = False
    http_time_between_calls = 0

    proxy_list = [
        'https://tpb.ipredator.se',
        'https://thepiratebay.se',
        'http://pirateproxy.ca',
        'http://tpb.al',
        'http://www.tpb.gr',
        'http://nl.tpb.li',
        'http://proxybay.eu',
        'https://www.getpirate.com',
        'http://piratebay.io', 
    ]

    def _searchOnTitle(self, title, movie, quality, results):

        page = 0
        total_pages = 1
        cats = self.getCatId(quality['identifier'])

        while page < total_pages:

            search_url = self.urls['search'] % (self.getDomain(), tryUrlencode('"%s" %s' % (title, movie['library']['year'])), page, ','.join(str(x) for x in cats))
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
                    for result in entries[2:]:
                        link = result.find(href = re.compile('torrent\/\d+\/'))
                        download = result.find(href = re.compile('magnet:'))

                        try:
                            size = re.search('Size (?P<size>.+),', six.text_type(result.select('font.detDesc')[0])).group('size')
                        except:
                            continue

                        if link and download:

                            def extra_score(item):
                                trusted = (0, 10)[result.find('img', alt = re.compile('Trusted')) is not None]
                                vip = (0, 20)[result.find('img', alt = re.compile('VIP')) is not None]
                                confirmed = (0, 30)[result.find('img', alt = re.compile('Helpers')) is not None]
                                moderated = (0, 50)[result.find('img', alt = re.compile('Moderator')) is not None]

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

    def correctProxy(self, data):
        return 'title="Pirate Search"' in data

    def getMoreInfo(self, item):
        full_description = self.getCache('tpb.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('div', attrs = {'class': 'nfo'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

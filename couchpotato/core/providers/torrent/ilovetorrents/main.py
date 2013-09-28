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


class ILoveTorrents(TorrentMagnetProvider):

    urls = {
         'detail': '%s/torrent/%s',         
         'search':  '%s/browse.php?search=%s&page=%s&cat=%s'
    }

    cat_ids = [
       (["41"], ['720p', '1080p', 'brrip']),
       (["19"], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr']),
       (["20"], ['dvdr'])
    ]

    cat_backup_id = 200
    disable_provider = False
    http_time_between_calls = 0

    proxy_list = [
        'http://www.ilovetorrents.me',
    ]

    def __init__(self):
        self.domain = self.conf('domain')
        super(ILoveTorrents, self).__init__()

    def _searchOnTitle(self, title, movie, quality, results):

        page = 0
        total_pages = 1
        cats = self.getCatId(quality['identifier'])

        while page < total_pages:

            search_url = self.urls['search'] % (self.getDomain(), tryUrlencode('"%s" %s' % (title, movie['library']['year'])), page, cats[0]))
            page += 1

            data = self.getHTMLData(search_url)

            if data:
                try:
                    soup = BeautifulSoup(data, "html5lib")
                
                    results_table = soup.find('table', attrs = {'class': 'koptekst'})

                    if not results_table:
                        return

                    try:
						pagelinks = soup.findAll(href=re.compile("page"))
                        pageNumbers = [int(re.search('page=(?P<pageNumber>.+'')', i["href"]).group('pageNumber')) for i in pagelinks]
                        total_pages = max(pageNumbers)
						
                    except:
                        pass

                    entries = results_table.find_all('tr')
					
                    for result in entries[1:]:
                        link = result.find(href = re.compile('details.php'))['href']
                        download = result.find('a', href = re.compile('download.php'))['href']                        
                        
                        try:
                            matches = re.search('>(?P<size>.+)<br/>(?P<unit>.B)', unicode(result.select('td.rowhead')[5]))
                            size = matches.group('size') + " " + matches.group('unit')

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
        return super(ILoveTorrents, self).isEnabled() and self.getDomain()

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
            log.error('No ILT proxies left, please add one in settings, or let us know which one to add on the forum.')
            return None

        return cleanHost(self.domain).rstrip('/') + url

    def getMoreInfo(self, item):
        full_description = self.getCache('tpb.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('div', attrs = {'class':'nfo'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

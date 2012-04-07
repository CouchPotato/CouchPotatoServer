from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from dateutil.parser import parse
from urllib import urlencode
import time
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class Newznab(NZBProvider, RSS):

    urls = {
        'download': 'get&id=%s',
        'detail': 'details&id=%s',
        'search': 'movie',
    }

    cat_ids = [
        ([2010], ['dvdr']),
        ([2030], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr']),
        ([2040], ['720p', '1080p']),
        ([2050], ['bd50']),
    ]
    cat_backup_id = 2000

    http_time_between_calls = 1 # Seconds

    def feed(self):

        hosts = self.getHosts()

        results = []
        for host in hosts:
            result = self.singleFeed(host)

            if result:
                results.extend(result)

        return results

    def singleFeed(self, host):

        results = []
        if self.isDisabled(host) or not self.isAvailable(self.getUrl(host['host'], self.urls['search'])):
            return results

        arguments = urlencode({
            't': self.cat_backup_id,
            'r': host['api_key'],
            'i': 58,
        })
        url = "%s?%s" % (cleanHost(host['host']) + 'rss', arguments)
        cache_key = 'newznab.%s.feed.%s' % (host['host'], arguments)

        results = self.createItems(url, cache_key, host, for_feed = True)

        return results


    def search(self, movie, quality):

        hosts = self.getHosts()

        results = []
        for host in hosts:
            result = self.singleSearch(host, movie, quality)

            if result:
                results.extend(result)

        return results

    def singleSearch(self, host, movie, quality):

        results = []
        if self.isDisabled(host) or not self.isAvailable(self.getUrl(host['host'], self.urls['search'])):
            return results

        cat_id = self.getCatId(quality['identifier'])
        arguments = urlencode({
            'imdbid': movie['library']['identifier'].replace('tt', ''),
            'cat': cat_id[0],
            'apikey': host['api_key'],
            't': self.urls['search'],
            'extended': 1
        })
        url = "%s&%s" % (self.getUrl(host['host'], self.urls['search']), arguments)

        cache_key = 'newznab.%s.%s.%s' % (host['host'], movie['library']['identifier'], cat_id[0])
        single_cat = (len(cat_id) == 1 and cat_id[0] != self.cat_backup_id)

        results = self.createItems(url, cache_key, host, single_cat = single_cat, movie = movie, quality = quality)

        return results

    def createItems(self, url, cache_key, host, single_cat = False, movie = None, quality = None, for_feed = False):
        results = []

        data = self.getCache(cache_key, url)
        if data:
            try:
                try:
                    data = XMLTree.fromstring(data)
                    nzbs = self.getElements(data, 'channel/item')
                except Exception, e:
                    log.debug('%s, %s' % (self.getName(), e))
                    return results

                results = []
                for nzb in nzbs:

                    date = ''
                    size = 0
                    for item in nzb:
                        if item.attrib.get('name') == 'size':
                            size = item.attrib.get('value')
                        elif item.attrib.get('name') == 'usenetdate':
                            date = item.attrib.get('value')

                    if date is '': log.info('Date not parsed properly or not available for %s: %s' % (host, self.getTextElement(nzb, "title")))
                    if size is 0: log.info('Size not parsed properly or not available for %s: %s' % (host, self.getTextElement(nzb, "title")))

                    id = self.getTextElement(nzb, "guid").split('/')[-1:].pop()
                    new = {
                        'id': id,
                        'provider': self.getName(),
                        'type': 'nzb',
                        'name': self.getTextElement(nzb, "title"),
                        'age': self.calculateAge(int(time.mktime(parse(date).timetuple()))),
                        'size': int(size) / 1024 / 1024,
                        'url': (self.getUrl(host['host'], self.urls['download']) % id) + self.getApiExt(host),
                        'download': self.download,
                        'detail_url': (self.getUrl(host['host'], self.urls['detail']) % id) + self.getApiExt(host),
                        'content': self.getTextElement(nzb, "description"),
                    }

                    if not for_feed:
                        new['score'] = fireEvent('score.calculate', new, movie, single = True)

                        is_correct_movie = fireEvent('searcher.correct_movie',
                                                     nzb = new, movie = movie, quality = quality,
                                                     imdb_results = True, single_category = single_cat, single = True)

                        if is_correct_movie:
                            results.append(new)
                            self.found(new)
                    else:
                        results.append(new)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from Newznab: %s' % host)
                return results

    def getHosts(self):

        uses = str(self.conf('use')).split(',')
        hosts = self.conf('host').split(',')
        api_keys = self.conf('api_key').split(',')

        list = []
        for nr in range(len(hosts)):
            list.append({
                'use': uses[nr],
                'host': hosts[nr],
                'api_key': api_keys[nr]
            })

        return list

    def belongsTo(self, url):

        hosts = self.getHosts()

        for host in hosts:
            result = super(Newznab, self).belongsTo(url, host = host['host'])
            if result:
                return result

        return

    def getUrl(self, host, type):
        return cleanHost(host) + 'api?t=' + type

    def isDisabled(self, host):
        return not self.isEnabled(host)

    def isEnabled(self, host):
        return NZBProvider.isEnabled(self) and host['host'] and host['api_key'] and int(host['use'])

    def getApiExt(self, host):
        return '&apikey=%s' % host['api_key']

from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import cleanHost, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
from dateutil.parser import parse
from urllib2 import HTTPError
from urlparse import urlparse
import time
import traceback
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class Newznab(NZBProvider, RSS):

    urls = {
        'download': 'get&id=%s',
        'detail': 'details&id=%s',
        'search': 'movie',
    }

    limits_reached = {}

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
        if self.isDisabled(host):
            return results

        arguments = tryUrlencode({
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
        if self.isDisabled(host):
            return results

        cat_id = self.getCatId(quality['identifier'])
        arguments = tryUrlencode({
            'imdbid': movie['library']['identifier'].replace('tt', ''),
            'cat': cat_id[0],
            'apikey': host['api_key'],
            'extended': 1
        })
        url = "%s&%s" % (self.getUrl(host['host'], self.urls['search']), arguments)

        cache_key = 'newznab.%s.%s.%s' % (host['host'], movie['library']['identifier'], cat_id[0])

        results = self.createItems(url, cache_key, host, movie = movie, quality = quality)

        return results

    def createItems(self, url, cache_key, host, movie = None, quality = None, for_feed = False):
        results = []

        data = self.getCache(cache_key, url, cache_timeout = 1800, headers = {'User-Agent': Env.getIdentifier()})
        if data:
            try:
                try:
                    data = XMLTree.fromstring(data)
                    nzbs = self.getElements(data, 'channel/item')
                except Exception, e:
                    log.debug('%s, %s', (self.getName(), e))
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

                    if date is '': log.debug('Date not parsed properly or not available for %s: %s', (host['host'], self.getTextElement(nzb, "title")))
                    if size is 0: log.debug('Size not parsed properly or not available for %s: %s', (host['host'], self.getTextElement(nzb, "title")))

                    id = self.getTextElement(nzb, "guid").split('/')[-1:].pop()
                    new = {
                        'id': id,
                        'provider': self.getName(),
                        'provider_extra': host['host'],
                        'type': 'nzb',
                        'name': self.getTextElement(nzb, "title"),
                        'age': self.calculateAge(int(time.mktime(parse(date).timetuple()))),
                        'size': int(size) / 1024 / 1024,
                        'url': (self.getUrl(host['host'], self.urls['download']) % id) + self.getApiExt(host),
                        'download': self.download,
                        'detail_url': '%sdetails/%s' % (cleanHost(host['host']), id),
                        'content': self.getTextElement(nzb, "description"),
                    }

                    if not for_feed:
                        is_correct_movie = fireEvent('searcher.correct_movie',
                                                     nzb = new, movie = movie, quality = quality,
                                                     imdb_results = True, single = True)

                        if is_correct_movie:
                            new['score'] = fireEvent('score.calculate', new, movie, single = True)
                            results.append(new)
                            self.found(new)
                    else:
                        results.append(new)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from Newznab: %s', host)
                return results

    def getHosts(self):

        uses = splitString(str(self.conf('use')))
        hosts = splitString(self.conf('host'))
        api_keys = splitString(self.conf('api_key'))

        list = []
        for nr in range(len(hosts)):
            list.append({
                'use': uses[nr],
                'host': hosts[nr],
                'api_key': api_keys[nr]
            })

        return list

    def belongsTo(self, url, provider = None):

        hosts = self.getHosts()

        for host in hosts:
            result = super(Newznab, self).belongsTo(url, host = host['host'], provider = provider)
            if result:
                return result

    def getUrl(self, host, type):
        return cleanHost(host) + 'api?t=' + type

    def isDisabled(self, host):
        return not self.isEnabled(host)

    def isEnabled(self, host):
        return NZBProvider.isEnabled(self) and host['host'] and host['api_key'] and int(host['use'])

    def getApiExt(self, host):
        return '&apikey=%s' % host['api_key']

    def download(self, url = '', nzb_id = ''):
        host = urlparse(url).hostname

        if self.limits_reached.get(host):
            # Try again in 3 hours
            if self.limits_reached[host] > time.time() - 10800:
                return 'try_next'

        try:
            data = self.urlopen(url, show_error = False)
            self.limits_reached[host] = False
            return data
        except HTTPError, e:
            if e.code == 503:
                response = e.read().lower()
                if 'maximum api' in response or 'download limit' in response:
                    if not self.limits_reached.get(host):
                        log.error('Limit reached for newznab provider: %s', host)
                    self.limits_reached[host] = time.time()
                    return 'try_next'

            log.error('Failed download from %s', (host, traceback.format_exc()))
            raise

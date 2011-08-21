from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import NZBProvider
from couchpotato.environment import Env
from dateutil.parser import parse
from urllib import urlencode
from urllib2 import URLError
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
        ([2000], ['brrip']),
        ([2010], ['dvdr']),
        ([2030], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr']),
        ([2040], ['720p', '1080p']),
    ]
    cat_backup_id = 2000

    time_between_searches = 1 # Seconds

    def __init__(self):
        super(NZBProvider, self).__init__()

        self.registerStatic(__file__)

    def getUrl(self, host, type):
        return cleanHost(host) + 'api?t=' + type

    def search(self, movie, quality):

        uses = str(self.conf('use')).split(',')
        hosts = self.conf('host').split(',')
        api_keys = self.conf('api_key').split(',')

        for nr in range(len(hosts)):
            self.singleSearch({
                'use': uses[nr],
                'host': hosts[nr],
                'api_key': api_keys[nr]
            }, movie, quality)

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

        try:
            data = self.getCache(cache_key)
            if not data:
                data = self.urlopen(url)
                self.setCache(cache_key, data)
        except (IOError, URLError):
            log.error('Failed to open %s.' % url)
            return results

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

                    for item in nzb:
                        if item.attrib.get('name') == 'size':
                            size = item.attrib.get('value')
                        elif item.attrib.get('name') == 'usenetdate':
                            date = item.attrib.get('value')

                    id = self.getTextElement(nzb, "guid").split('/')[-1:].pop()
                    new = {
                        'id': id,
                        'type': 'nzb',
                        'name': self.getTextElement(nzb, "title"),
                        'age': self.calculateAge(int(time.mktime(parse(date).timetuple()))),
                        'size': int(size) / 1024 / 1024,
                        'url': (self.getUrl(host['host'], self.urls['download']) % id) + self.getApiExt(host),
                        'detail_url': (self.getUrl(host['host'], self.urls['detail']) % id) + self.getApiExt(host),
                        'content': self.getTextElement(nzb, "description"),
                    }
                    new['score'] = fireEvent('score.calculate', new, movie, single = True)

                    is_correct_movie = fireEvent('searcher.correct_movie',
                                                 nzb = new, movie = movie, quality = quality,
                                                 imdb_results = True, single_category = single_cat, single = True)

                    if is_correct_movie:
                        results.append(new)
                        self.found(new)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from Newznab')
                return False

        return results

    def isDisabled(self, host):
        return not self.isEnabled(host)

    def isEnabled(self, host):
        return NZBProvider.isEnabled(self) and host['host'] and host['api_key'] and int(host['use'])

    def getApiExt(self, host):
        return '&apikey=%s' % host['api_key']

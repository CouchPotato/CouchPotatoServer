from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import cleanHost, splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import ResultList
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
from dateutil.parser import parse
from urllib2 import HTTPError
from urlparse import urlparse
import time
import traceback

log = CPLog(__name__)


class Newznab(NZBProvider, RSS):

    urls = {
        'download': 'get&id=%s',
        'detail': 'details&id=%s',
        'search': 'movie',
    }

    limits_reached = {}

    http_time_between_calls = 1 # Seconds

    def search(self, movie, quality):
        hosts = self.getHosts()

        results = ResultList(self, movie, quality, imdb_results = True)

        for host in hosts:
            if self.isDisabled(host):
                continue

            self._searchOnHost(host, movie, quality, results)

        return results

    def _searchOnHost(self, host, movie, quality, results):

        arguments = tryUrlencode({
            'imdbid': movie['library']['identifier'].replace('tt', ''),
            'apikey': host['api_key'],
            'extended': 1
        })
        url = '%s&%s' % (self.getUrl(host['host'], self.urls['search']), arguments)

        nzbs = self.getRSSData(url, cache_timeout = 1800, headers = {'User-Agent': Env.getIdentifier()})

        for nzb in nzbs:

            date = None
            for item in nzb:
                if item.attrib.get('name') == 'usenetdate':
                    date = item.attrib.get('value')
                    break

            if not date:
                date = self.getTextElement(nzb, 'pubDate')

            nzb_id = self.getTextElement(nzb, 'guid').split('/')[-1:].pop()
            name = self.getTextElement(nzb, 'title')

            if not name:
                continue

            results.append({
                'id': nzb_id,
                'provider_extra': urlparse(host['host']).hostname or host['host'],
                'name': self.getTextElement(nzb, 'title'),
                'age': self.calculateAge(int(time.mktime(parse(date).timetuple()))),
                'size': int(self.getElement(nzb, 'enclosure').attrib['length']) / 1024 / 1024,
                'url': (self.getUrl(host['host'], self.urls['download']) % tryUrlencode(nzb_id)) + self.getApiExt(host),
                'detail_url': '%sdetails/%s' % (cleanHost(host['host']), tryUrlencode(nzb_id)),
                'content': self.getTextElement(nzb, 'description'),
                'score': host['extra_score'],
            })

    def getHosts(self):

        uses = splitString(str(self.conf('use')))
        hosts = splitString(self.conf('host'))
        api_keys = splitString(self.conf('api_key'))
        extra_score = splitString(self.conf('extra_score'))

        list = []
        for nr in range(len(hosts)):
            list.append({
                'use': uses[nr],
                'host': hosts[nr],
                'api_key': api_keys[nr],
                'extra_score': tryInt(extra_score[nr]) if len(extra_score) > nr else 0
            })

        return list

    def belongsTo(self, url, provider = None):

        hosts = self.getHosts()

        for host in hosts:
            result = super(Newznab, self).belongsTo(url, host = host['host'], provider = provider)
            if result:
                return result

    def getUrl(self, host, type):
        if '?page=newznabapi' in host:
            return cleanHost(host)[:-1] + '&t=' + type

        return cleanHost(host) + 'api?t=' + type

    def isDisabled(self, host = None):
        return not self.isEnabled(host)

    def isEnabled(self, host = None):

        # Return true if at least one is enabled and no host is given
        if host is None:
            for host in self.getHosts():
                if self.isEnabled(host):
                    return True
            return False

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

            log.error('Failed download from %s: %s', (host, traceback.format_exc()))

        return 'try_next'

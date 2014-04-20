from urllib2 import HTTPError
from urlparse import urlparse
import time
import traceback
import re
import urllib2

from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import cleanHost, splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.base import ResultList
from couchpotato.core.media._base.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
from dateutil.parser import parse


log = CPLog(__name__)


class Base(NZBProvider, RSS):

    urls = {
        'detail': 'details/%s',
        'download': 't=get&id=%s'
    }

    passwords_regex = 'password|wachtwoord'
    limits_reached = {}

    http_time_between_calls = 1  # Seconds

    def search(self, media, quality):
        hosts = self.getHosts()

        results = ResultList(self, media, quality, imdb_results = True)

        for host in hosts:
            if self.isDisabled(host):
                continue

            self._searchOnHost(host, media, quality, results)

        return results

    def _searchOnHost(self, host, media, quality, results):

        query = self.buildUrl(media, host['api_key'])
        url = '%s&%s' % (self.getUrl(host['host']), query)
        nzbs = self.getRSSData(url, cache_timeout = 1800, headers = {'User-Agent': Env.getIdentifier()})

        for nzb in nzbs:

            date = None
            spotter = None
            for item in nzb:
                if date and spotter:
                    break
                if item.attrib.get('name') == 'usenetdate':
                    date = item.attrib.get('value')
                    break

                # Get the name of the person who posts the spot
                if item.attrib.get('name') == 'poster':
                    if "@spot.net" in item.attrib.get('value'):
                        spotter = item.attrib.get('value').split("@")[0]
                        continue

            if not date:
                date = self.getTextElement(nzb, 'pubDate')

            nzb_id = self.getTextElement(nzb, 'guid').split('/')[-1:].pop()
            name = self.getTextElement(nzb, 'title')

            if not name:
                continue

            name_extra = ''
            if spotter:
                name_extra = spotter

            description = ''
            if "@spot.net" in nzb_id:
                try:
                    # Get details for extended description to retrieve passwords
                    query = self.buildDetailsUrl(nzb_id, host['api_key'])
                    url = '%s&%s' % (self.getUrl(host['host']), query)
                    nzb_details = self.getRSSData(url, cache_timeout = 1800, headers = {'User-Agent': Env.getIdentifier()})[0]

                    description = self.getTextElement(nzb_details, 'description')

                    # Extract a password from the description
                    password = re.search('(?:' + self.passwords_regex + ')(?: *)(?:\:|\=)(?: *)(.*?)\<br\>|\n|$', description, flags = re.I).group(1)
                    if password:
                        name = name + ' {{%s}}' % password.strip()
                except:
                    log.debug('Error getting details of "%s": %s', (name, traceback.format_exc()))

            results.append({
                'id': nzb_id,
                'provider_extra': urlparse(host['host']).hostname or host['host'],
                'name': toUnicode(name),
                'name_extra': name_extra,
                'age': self.calculateAge(int(time.mktime(parse(date).timetuple()))),
                'size': int(self.getElement(nzb, 'enclosure').attrib['length']) / 1024 / 1024,
                'url': ((self.getUrl(host['host']) + self.urls['download']) % tryUrlencode(nzb_id)) + self.getApiExt(host),
                'detail_url': (cleanHost(host['host']) + self.urls['detail']) % tryUrlencode(nzb_id),
                'content': self.getTextElement(nzb, 'description'),
                'description': description,
                'score': host['extra_score'],
            })

    def getHosts(self):

        uses = splitString(str(self.conf('use')), clean = False)
        hosts = splitString(self.conf('host'), clean = False)
        api_keys = splitString(self.conf('api_key'), clean = False)
        extra_score = splitString(self.conf('extra_score'), clean = False)
        custom_tags = splitString(self.conf('custom_tag'), clean = False)

        list = []
        for nr in range(len(hosts)):

            try: key = api_keys[nr]
            except: key = ''

            try: host = hosts[nr]
            except: host = ''

            try: score = tryInt(extra_score[nr])
            except: score = 0

            try: custom_tag = custom_tags[nr]
            except: custom_tag = ''

            list.append({
                'use': uses[nr],
                'host': host,
                'api_key': key,
                'extra_score': score,
                'custom_tag': custom_tag
            })

        return list

    def belongsTo(self, url, provider = None, host = None):

        hosts = self.getHosts()

        for host in hosts:
            result = super(Base, self).belongsTo(url, host = host['host'], provider = provider)
            if result:
                return result

    def getUrl(self, host):
        if '?page=newznabapi' in host:
            return cleanHost(host)[:-1] + '&'

        return cleanHost(host) + 'api?'

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
            # Get final redirected url
            log.debug('Checking %s for redirects.', url)
            req = urllib2.Request(url)
            req.add_header('User-Agent', self.user_agent)
            res = urllib2.urlopen(req)
            finalurl = res.geturl()
            if finalurl != url:
                log.debug('Redirect url used: %s', finalurl)

            data = self.urlopen(finalurl, show_error = False)
            self.limits_reached[host] = False
            return data
        except HTTPError as e:
            if e.code == 503:
                response = e.read().lower()
                if 'maximum api' in response or 'download limit' in response:
                    if not self.limits_reached.get(host):
                        log.error('Limit reached for newznab provider: %s', host)
                    self.limits_reached[host] = time.time()
                    return 'try_next'

            log.error('Failed download from %s: %s', (host, traceback.format_exc()))

        return 'try_next'

    def buildDetailsUrl(self, nzb_id, api_key):
        query = tryUrlencode({
            't': 'details',
            'id': nzb_id,
            'apikey': api_key,
        })
        return query



config = [{
    'name': 'newznab',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'nzb_providers',
            'name': 'newznab',
            'order': 10,
            'description': 'Enable <a href="http://newznab.com/" target="_blank">NewzNab</a> such as <a href="https://nzb.su" target="_blank">NZB.su</a>, \
                <a href="https://nzbs.org" target="_blank">NZBs.org</a>, <a href="http://dognzb.cr/" target="_blank">DOGnzb.cr</a>, \
                <a href="https://github.com/spotweb/spotweb" target="_blank">Spotweb</a>, <a href="https://nzbgeek.info/" target="_blank">NZBGeek</a>, \
                <a href="https://smackdownonyou.com" target="_blank">SmackDown</a>, <a href="https://www.nzbfinder.ws" target="_blank">NZBFinder</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True,
                },
                {
                    'name': 'use',
                    'default': '0,0,0,0,0,0'
                },
                {
                    'name': 'host',
                    'default': 'api.nzb.su,dognzb.cr,nzbs.org,https://index.nzbgeek.info, https://smackdownonyou.com, https://www.nzbfinder.ws',
                    'description': 'The hostname of your newznab provider',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'default': '0,0,0,0,0,0',
                    'description': 'Starting score for each release found via this provider.',
                },
                {
                    'name': 'custom_tag',
                    'advanced': True,
                    'label': 'Custom tag',
                    'default': ',,,,,',
                    'description': 'Add custom tags, for example add rls=1 to get only scene releases from nzbs.org',
                },
                {
                    'name': 'api_key',
                    'default': ',,,,,',
                    'label': 'Api Key',
                    'description': 'Can be found on your profile page',
                    'type': 'combined',
                    'combine': ['use', 'host', 'api_key', 'extra_score', 'custom_tag'],
                },
            ],
        },
    ],
}]

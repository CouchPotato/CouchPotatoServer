from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import tryFloat, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from urlparse import urlparse
import cookielib
import re
import time
import traceback
import urllib2


log = CPLog(__name__)


class Provider(Plugin):

    type = None # movie, nzb, torrent, subtitle, trailer
    http_time_between_calls = 10 # Default timeout for url requests

    last_available_check = {}
    is_available = {}

    def isAvailable(self, test_url):

        if Env.get('dev'): return True

        now = time.time()
        host = urlparse(test_url).hostname

        if self.last_available_check.get(host) < now - 900:
            self.last_available_check[host] = now

            try:
                self.urlopen(test_url, 30)
                self.is_available[host] = True
            except:
                log.error('"%s" unavailable, trying again in an 15 minutes.', host)
                self.is_available[host] = False

        return self.is_available.get(host, False)


class YarrProvider(Provider):

    cat_ids = []

    sizeGb = ['gb', 'gib']
    sizeMb = ['mb', 'mib']
    sizeKb = ['kb', 'kib']

    login_opener = None

    def __init__(self):
        addEvent('provider.belongs_to', self.belongsTo)

        addEvent('%s.search' % self.type, self.search)
        addEvent('yarr.search', self.search)

        addEvent('nzb.feed', self.feed)

    def login(self):

        try:
            cookiejar = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
            urllib2.install_opener(opener)
            log.info2('Logging into %s', self.urls['login'])
            f = opener.open(self.urls['login'], self.getLoginParams())
            f.read()
            f.close()
            self.login_opener = opener
            return True
        except:
            log.error('Failed to login %s: %s', (self.getName(), traceback.format_exc()))

        return False

    def loginDownload(self, url = '', nzb_id = ''):
        try:
            if not self.login_opener and not self.login():
                log.error('Failed downloading from %s', self.getName())
            return self.urlopen(url, opener = self.login_opener)
        except:
            log.error('Failed downloading from %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return ''

    def download(self, url = '', nzb_id = ''):
        try:
            return self.urlopen(url, headers = {'User-Agent': Env.getIdentifier()}, show_error = False)
        except:
            log.error('Failed getting nzb from %s: %s', (self.getName(), traceback.format_exc()))

        return 'try_next'

    def feed(self):
        return []

    def search(self, movie, quality):
        return []

    def belongsTo(self, url, provider = None, host = None):
        try:
            if provider and provider == self.getName():
                return self

            hostname = urlparse(url).hostname
            if host and hostname in host:
                return self
            else:
                for url_type in self.urls:
                    download_url = self.urls[url_type]
                    if hostname in download_url:
                        return self
        except:
            log.debug('Url % s doesn\'t belong to %s', (url, self.getName()))

        return

    def parseSize(self, size):

        sizeRaw = size.lower()
        size = tryFloat(re.sub(r'[^0-9.]', '', size).strip())

        for s in self.sizeGb:
            if s in sizeRaw:
                return size * 1024

        for s in self.sizeMb:
            if s in sizeRaw:
                return size

        for s in self.sizeKb:
            if s in sizeRaw:
                return size / 1024

        return 0

    def getCatId(self, identifier):

        for cats in self.cat_ids:
            ids, qualities = cats
            if identifier in qualities:
                return ids

        return [self.cat_backup_id]

    def found(self, new):
        if not new.get('provider_extra'):
            new['provider_extra'] = ''
        else:
            new['provider_extra'] = ', %s' % new['provider_extra']

        log.info('Found: score(%(score)s) on %(provider)s%(provider_extra)s: %(name)s', new)

    def removeDuplicateResults(self, results):

        result_ids = []
        new_results = []

        for result in results:
            if result['id'] not in result_ids:
                new_results.append(result)
                result_ids.append(result['id'])

        return new_results

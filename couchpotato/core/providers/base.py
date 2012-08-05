from couchpotato.core.event import addEvent
from couchpotato.core.helpers.variable import tryFloat
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from urlparse import urlparse
import re
import time


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

    def __init__(self):
        addEvent('provider.belongs_to', self.belongsTo)

        addEvent('%s.search' % self.type, self.search)
        addEvent('yarr.search', self.search)

        addEvent('nzb.feed', self.feed)

    def download(self, url = '', nzb_id = ''):
        return self.urlopen(url)

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
        log.info('Found: score(%(score)s) on %(provider)s: %(name)s', new)

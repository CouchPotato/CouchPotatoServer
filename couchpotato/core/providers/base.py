from couchpotato.core.event import addEvent
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

        if Env.getValue('debug'): return True

        now = time.time()
        host = urlparse(test_url).hostname

        if self.last_available_check.get(host) < now - 900:
            self.last_available_check[host] = now

            try:
                self.urlopen(test_url, 30)
                self.is_available[host] = True
            except:
                log.error('"%s" unavailable, trying again in an 15 minutes.' % host)
                self.is_available[host] = False

        return self.is_available.get(host, False)


class YarrProvider(Provider):

    cat_ids = []

    sizeGb = ['gb', 'gib']
    sizeMb = ['mb', 'mib']
    sizeKb = ['kb', 'kib']

    def __init__(self):
        addEvent('provider.belongs_to', self.belongsTo)

    def belongsTo(self, url, host = None):
        try:
            hostname = urlparse(url).hostname
            download_url = host if host else self.urls['download']
            if hostname in download_url:
                return self
        except:
            log.debug('Url % s doesn\'t belong to %s' % (url, self.getName()))

        return

    def parseSize(self, size):

        sizeRaw = size.lower()
        size = float(re.sub(r'[^0-9.]', '', size).strip())

        for s in self.sizeGb:
            if s in sizeRaw:
                return int(size) * 1024

        for s in self.sizeMb:
            if s in sizeRaw:
                return int(size)

        for s in self.sizeKb:
            if s in sizeRaw:
                return int(size) / 1024

        return 0

    def getCatId(self, identifier):

        for cats in self.cat_ids:
            ids, qualities = cats
            if identifier in qualities:
                return ids

        return [self.cat_backup_id]

    def found(self, new):
        log.info('Found: score(%(score)s): %(name)s' % new)

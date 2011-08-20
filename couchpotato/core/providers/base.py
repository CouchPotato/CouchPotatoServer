from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from urllib2 import URLError
from urlparse import urlparse
import math
import re
import socket
import time
import urllib
import urllib2

log = CPLog(__name__)


class Provider(Plugin):

    type = None # movie, nzb, torrent, subtitle, trailer
    time_between_searches = 10 # Default timeout for url requests

    last_use = {}
    last_available_check = {}
    is_available = {}

    def getCache(self, cache_key):
        cache = Env.get('cache').get(cache_key)
        if cache:
            log.debug('Getting cache %s' % cache_key)
            return cache

    def setCache(self, cache_key, value):
        log.debug('Setting cache %s' % cache_key)
        Env.get('cache').set(cache_key, value)

    def isAvailable(self, test_url):

        if Env.get('debug'): return True

        now = time.time()
        host = urlparse(test_url).hostname

        if self.last_available_check.get(host) < now - 900:
            self.last_available_check[host] = now
            try:
                self.urlopen(test_url, 30)
                self.is_available[host] = True
            except (IOError, URLError):
                log.error('%s unavailable, trying again in an 15 minutes.' % self.name)
                self.is_available[host] = False

        return self.is_available[host]

    def urlopen(self, url, timeout = 10, params = {}):

        socket.setdefaulttimeout(timeout)

        host = urlparse(url).hostname
        self.wait(host)

        try:
            log.info('Opening url: %s, params: %s' % (url, params))
            request = urllib2.Request(url, urllib.urlencode(params))
            data = urllib2.urlopen(request).read()
        except IOError, e:
            log.error('Failed opening url, %s: %s' % (url, e))
            data = ''

        self.last_use[host] = time.time()

        return data

    def wait(self, host = ''):
        now = time.time()

        last_use = self.last_use.get(host, 0)

        wait = math.ceil(last_use - now + self.time_between_searches)

        if wait > 0:
            log.debug('Waiting for %s, %d seconds' % (self.getName(), wait))
            time.sleep(last_use - now + self.time_between_searches)


class MovieProvider(Provider):
    type = 'movie'


class YarrProvider(Provider):

    cat_ids = []

    sizeGb = ['gb', 'gib']
    sizeMb = ['mb', 'mib']
    sizeKb = ['kb', 'kib']

    def parseSize(self, size):

        sizeRaw = size.lower()
        size = re.sub(r'[^0-9.]', '', size).strip()

        for s in self.sizeGb:
            if s in sizeRaw:
                return float(size) * 1024

        for s in self.sizeMb:
            if s in sizeRaw:
                return float(size)

        for s in self.sizeKb:
            if s in sizeRaw:
                return float(size) / 1024

        return 0

    def getCatId(self, identifier):

        for cats in self.cat_ids:
            ids, qualities = cats
            if identifier in qualities:
                return ids

        return [self.cat_backup_id]

    def found(self, new):
        log.info('Found: score(%(score)s): %(name)s' % new)


class NZBProvider(YarrProvider):
    type = 'nzb'

    time_between_searches = 10 # Seconds

    def calculateAge(self, unix):
        return int(time.time() - unix) / 24 / 60 / 60


class TorrentProvider(YarrProvider):
    type = 'torrent'


class SubtitleProvider(Provider):
    type = 'subtitle'


class TrailerProvider(Provider):
    type = 'trailer'

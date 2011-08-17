from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from urllib2 import URLError
import math
import re
import socket
import time
import urllib2

log = CPLog(__name__)


class Provider(Plugin):

    type = None # movie, nzb, torrent, subtitle, trailer
    time_between_searches = 10 # Default timeout for url requests

    last_use = 0
    last_available_check = 0
    is_available = 0

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

        if self.last_available_check < now - 900:
            self.last_available_check = now
            try:
                self.urlopen(test_url, 30)
                self.is_available = True
            except (IOError, URLError):
                log.error('%s unavailable, trying again in an 15 minutes.' % self.name)
                self.is_available = False

        return self.is_available

    def urlopen(self, url, timeout = 10, username = None, password = None):

        socket.setdefaulttimeout(timeout)
        self.wait()

        try:
            log.info('Opening url: %s' % url)
            if username and password:
                passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
                passman.add_password(None, url, username, password)
                authhandler = urllib2.HTTPBasicAuthHandler(passman)
                opener = urllib2.build_opener(authhandler)
                data = opener.open(url).read()
            else:
                data = urllib2.urlopen(url).read()

        except IOError, e:
            log.error('Failed opening url, %s: %s' % (url, e))
            data = ''

        self.last_use = time.time()

        return data

    def wait(self):
        now = time.time()
        wait = math.ceil(self.last_use - now + self.time_between_searches)

        if wait > 0:
            log.debug('Waiting for %s, %d seconds' % (self.getName(), wait))
            time.sleep(self.last_use - now + self.time_between_searches)


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

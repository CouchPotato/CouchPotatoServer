from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import tryFloat, mergeDicts, md5, \
    possibleTitles, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from urlparse import urlparse
import cookielib
import json
import re
import time
import traceback
import urllib2
import xml.etree.ElementTree as XMLTree


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

    def getJsonData(self, url, **kwargs):

        data = self.getCache(md5(url), url, **kwargs)

        if data:
            try:
                return json.loads(data)
            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

        return []

    def getRSSData(self, url, **kwargs):

        data = self.getCache(md5(url), url, **kwargs)

        if data:
            try:
                data = XMLTree.fromstring(data)
                return self.getElements(data, 'channel/item')
            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

        return []

    def getHTMLData(self, url, **kwargs):
        return self.getCache(md5(url), url, **kwargs)


class YarrProvider(Provider):

    cat_ids = []

    sizeGb = ['gb', 'gib']
    sizeMb = ['mb', 'mib']
    sizeKb = ['kb', 'kib']

    login_opener = None

    def __init__(self):
        addEvent('provider.belongs_to', self.belongsTo)
        addEvent('yarr.search', self.search)

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

    def search(self, movie, quality):

        if self.isDisabled():
            return []

        # Login if needed
        if self.urls.get('login') and (not self.login_opener and not self.login()):
            log.error('Failed to login to: %s', self.getName())
            return []

        # Create result container
        imdb_results = hasattr(self, '_search')
        results = ResultList(self, movie, quality, imdb_results = imdb_results)

        # Do search based on imdb id
        if imdb_results:
            self._search(movie, quality, results)
        # Search possible titles
        else:
            for title in possibleTitles(getTitle(movie['library'])):
                self._searchOnTitle(title, movie, quality, results)

        return results

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


class ResultList(list):

    result_ids = None
    provider = None
    movie = None
    quality = None

    def __init__(self, provider, movie, quality, **kwargs):

        self.result_ids = []
        self.provider = provider
        self.movie = movie
        self.quality = quality
        self.kwargs = kwargs

        super(ResultList, self).__init__()

    def extend(self, results):
        for r in results:
            self.append(r)

    def append(self, result):

        new_result = self.fillResult(result)

        is_correct_movie = fireEvent('searcher.correct_movie',
                                     nzb = new_result, movie = self.movie, quality = self.quality,
                                     imdb_results = self.kwargs.get('imdb_results', False), single = True)

        if is_correct_movie and new_result['id'] not in self.result_ids:
            new_result['score'] += fireEvent('score.calculate', new_result, self.movie, single = True)

            self.found(new_result)
            self.result_ids.append(result['id'])

            super(ResultList, self).append(new_result)

    def fillResult(self, result):

        defaults = {
            'id': 0,
            'type': self.provider.type,
            'provider': self.provider.getName(),
            'download': self.provider.download,
            'url': '',
            'name': '',
            'age': 0,
            'size': 0,
            'description': '',
            'score': 0
        }

        return mergeDicts(defaults, result)

    def found(self, new_result):
        if not new_result.get('provider_extra'):
            new_result['provider_extra'] = ''
        else:
            new_result['provider_extra'] = ', %s' % new_result['provider_extra']

        log.info('Found: score(%(score)s) on %(provider)s%(provider_extra)s: %(name)s', new_result)

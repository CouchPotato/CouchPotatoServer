from urlparse import urlparse
import json
import re
import time
import traceback
import xml.etree.ElementTree as XMLTree

from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import ss
from couchpotato.core.helpers.variable import tryFloat, mergeDicts, md5, \
    possibleTitles
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env


log = CPLog(__name__)


class MultiProvider(Plugin):

    def __init__(self):
        self._classes = []

        for Type in self.getTypes():
            klass = Type()

            # Overwrite name so logger knows what we're talking about
            klass.setName('%s:%s' % (self.getName(), klass.getName()))

            self._classes.append(klass)

    def getTypes(self):
        return []

    def getClasses(self):
        return self._classes


class Provider(Plugin):

    type = None  # movie, show, subtitle, trailer, ...
    http_time_between_calls = 10  # Default timeout for url requests

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

    def getJsonData(self, url, decode_from = None, **kwargs):

        cache_key = md5(url)
        data = self.getCache(cache_key, url, **kwargs)

        if data:
            try:
                data = data.strip()
                if decode_from:
                    data = data.decode(decode_from)

                return json.loads(data)
            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

        return []

    def getRSSData(self, url, item_path = 'channel/item', **kwargs):

        cache_key = md5(url)
        data = self.getCache(cache_key, url, **kwargs)

        if data and len(data) > 0:
            try:
                data = XMLTree.fromstring(ss(data))
                return self.getElements(data, item_path)
            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

        return []

    def getHTMLData(self, url, **kwargs):

        cache_key = md5(url)
        return self.getCache(cache_key, url, **kwargs)


class YarrProvider(Provider):

    protocol = None  # nzb, torrent, torrent_magnet

    cat_ids = {}
    cat_backup_id = None

    size_gb = ['gb', 'gib']
    size_mb = ['mb', 'mib']
    size_kb = ['kb', 'kib']

    last_login_check = None

    def __init__(self):
        addEvent('provider.enabled_protocols', self.getEnabledProtocol)
        addEvent('provider.belongs_to', self.belongsTo)
        addEvent('provider.search.%s.%s' % (self.protocol, self.type), self.search)

    def getEnabledProtocol(self):
        if self.isEnabled():
            return self.protocol
        else:
            return []

    def login(self):

        # Check if we are still logged in every hour
        now = time.time()
        if self.last_login_check and self.last_login_check < (now - 3600):
            try:
                output = self.urlopen(self.urls['login_check'])
                if self.loginCheckSuccess(output):
                    self.last_login_check = now
                    return True
            except: pass
            self.last_login_check = None

        if self.last_login_check:
            return True

        try:
            output = self.urlopen(self.urls['login'], data = self.getLoginParams())

            if self.loginSuccess(output):
                self.last_login_check = now
                return True

            error = 'unknown'
        except:
            error = traceback.format_exc()

        self.last_login_check = None
        log.error('Failed to login %s: %s', (self.getName(), error))
        return False

    def loginSuccess(self, output):
        return True

    def loginCheckSuccess(self, output):
        return True

    def loginDownload(self, url = '', nzb_id = ''):
        try:
            if not self.login():
                log.error('Failed downloading from %s', self.getName())
            return self.urlopen(url)
        except:
            log.error('Failed downloading from %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return {}

    def download(self, url = '', nzb_id = ''):
        try:
            return self.urlopen(url, headers = {'User-Agent': Env.getIdentifier()}, show_error = False)
        except:
            log.error('Failed getting nzb from %s: %s', (self.getName(), traceback.format_exc()))

        return 'try_next'

    def search(self, media, quality):

        if self.isDisabled():
            return []

        # Login if needed
        if self.urls.get('login') and not self.login():
            log.error('Failed to login to: %s', self.getName())
            return []

        # Create result container
        imdb_results = hasattr(self, '_search')
        results = ResultList(self, media, quality, imdb_results = imdb_results)

        # Do search based on imdb id
        if imdb_results:
            self._search(media, quality, results)
        # Search possible titles
        else:
            media_title = fireEvent('library.query', media, include_year = False, single = True)

            for title in possibleTitles(media_title):
                self._searchOnTitle(title, media, quality, results)

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
            log.debug('Url %s doesn\'t belong to %s', (url, self.getName()))

        return

    def parseSize(self, size):

        size_raw = size.lower()
        size = tryFloat(re.sub(r'[^0-9.]', '', size).strip())

        for s in self.size_gb:
            if s in size_raw:
                return size * 1024

        for s in self.size_mb:
            if s in size_raw:
                return size

        for s in self.size_kb:
            if s in size_raw:
                return size / 1024

        return 0

    def getCatId(self, quality = None):
        if not quality: quality = {}
        identifier = quality.get('identifier')

        want_3d = False
        if quality.get('custom'):
            want_3d = quality['custom'].get('3d')

        for ids, qualities in self.cat_ids:
            if identifier in qualities or (want_3d and '3d' in qualities):
                return ids

        if self.cat_backup_id:
            return [self.cat_backup_id]

        return []


class ResultList(list):

    result_ids = None
    provider = None
    media = None
    quality = None

    def __init__(self, provider, media, quality, **kwargs):

        self.result_ids = []
        self.provider = provider
        self.media = media
        self.quality = quality
        self.kwargs = kwargs

        super(ResultList, self).__init__()

    def extend(self, results):
        for r in results:
            self.append(r)

    def append(self, result):

        new_result = self.fillResult(result)

        is_correct = fireEvent('searcher.correct_release', new_result, self.media, self.quality,
                               imdb_results = self.kwargs.get('imdb_results', False), single = True)

        if is_correct and new_result['id'] not in self.result_ids:
            is_correct_weight = float(is_correct)

            new_result['score'] += fireEvent('score.calculate', new_result, self.media, single = True)

            old_score = new_result['score']
            new_result['score'] = int(old_score * is_correct_weight)

            log.info('Found correct release with weight %.02f, old_score(%d) now scaled to score(%d)', (
                is_correct_weight,
                old_score,
                new_result['score']
            ))

            self.found(new_result)
            self.result_ids.append(result['id'])

            super(ResultList, self).append(new_result)

    def fillResult(self, result):

        defaults = {
            'id': 0,
            'protocol': self.provider.protocol,
            'type': self.provider.type,
            'provider': self.provider.getName(),
            'download': self.provider.loginDownload if self.provider.urls.get('login') else self.provider.download,
            'seed_ratio': Env.setting('seed_ratio', section = self.provider.getName().lower(), default = ''),
            'seed_time': Env.setting('seed_time', section = self.provider.getName().lower(), default = ''),
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

from couchpotato.core.event import addEvent
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import NZBProvider
from dateutil.parser import parse
from urllib import urlencode
from urllib2 import URLError
import time

log = CPLog(__name__)


class Newznab(NZBProvider):

    urls = {
        'download': 'get&id=%s%s',
        'detail': 'details&id=%s',
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
        addEvent('provider.nzb.search', self.search)

    def getUrl(self, type):
        return cleanHost(self.conf('host')) + 'api?t=' + type

    def search(self, movie, quality):

        self.cleanCache();

        results = []
        if not self.enabled() or not self.isAvailable(self.getUrl(self.searchUrl)):
            return results

        catId = self.getCatId(type)
        arguments = urlencode({
            'imdbid': movie.imdb.replace('tt', ''),
            'cat': catId,
            'apikey': self.conf('apikey'),
            't': self.searchUrl,
            'extended': 1
        })
        url = "%s&%s" % (self.getUrl(self.searchUrl), arguments)
        cacheId = str(movie.imdb) + '-' + str(catId)
        singleCat = (len(self.catIds.get(catId)) == 1 and catId != self.catBackupId)

        try:
            cached = False
            if(self.cache.get(cacheId)):
                data = True
                cached = True
                log.info('Getting RSS from cache: %s.' % cacheId)
            else:
                log.info('Searching: %s' % url)
                data = self.urlopen(url)
                self.cache[cacheId] = {
                    'time': time.time()
                }

        except (IOError, URLError):
            log.error('Failed to open %s.' % url)
            return results

        if data:
            try:
                try:
                    if cached:
                        xml = self.cache[cacheId]['xml']
                    else:
                        xml = self.getItems(data)
                        self.cache[cacheId]['xml'] = xml
                except:
                    log.debug('No valid xml or to many requests.' % self.name)
                    return results

                results = []
                for nzb in xml:

                    for item in nzb:
                        if item.attrib.get('name') == 'size':
                            size = item.attrib.get('value')
                        elif item.attrib.get('name') == 'usenetdate':
                            date = item.attrib.get('value')

                    new = self.feedItem()
                    new.id = self.gettextelement(nzb, "guid").split('/')[-1:].pop()
                    new.type = 'nzb'
                    new.name = self.gettextelement(nzb, "title")
                    new.date = int(time.mktime(parse(date).timetuple()))
                    new.size = int(size) / 1024 / 1024
                    new.url = self.downloadLink(new.id)
                    new.detailUrl = self.detailLink(new.id)
                    new.content = self.gettextelement(nzb, "description")
                    new.score = self.calcScore(new, movie)

                    if new.date > time.time() - (int(self.config.get('NZB', 'retention')) * 24 * 60 * 60) and self.isCorrectMovie(new, movie, type, imdbResults = True, singleCategory = singleCat):
                        results.append(new)
                        log.info('Found: %s' % new.name)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from Newznab')
                return False

        return results

    def isEnabled(self):
        return NZBProvider.isEnabled(self) and self.conf('enabled') and self.conf('host') and self.conf('apikey')

    def getApiExt(self):
        return '&apikey=%s' % self.conf('apikey')

    def downloadLink(self, id):
        return self.getUrl(self.downloadUrl) % (id, self.getApiExt())

    def detailLink(self, id):
        return self.getUrl(self.detailUrl) % id

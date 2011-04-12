from app.config.cplog import CPLog
from app.lib.provider.yarr.base import nzbBase
from dateutil.parser import parse
from urllib import urlencode
from urllib2 import URLError
import time

log = CPLog(__name__)

class nzbMatrix(nzbBase):
    """Api for NZBMatrix"""

    name = 'NZBMatrix'
    downloadUrl = 'https://api.nzbmatrix.com/v1.1/download.php?id=%s%s'
    detailUrl = 'https://nzbmatrix.com/nzb-details.php?id=%s&hit=1'
    searchUrl = 'http://rss.nzbmatrix.com/rss.php'

    catIds = {
        42: ['720p', '1080p'],
        2: ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr'],
        54: ['brrip'],
        1: ['dvdr']
    }
    catBackupId = 2

    timeBetween = 10 # Seconds

    def __init__(self, config):
        log.info('Using NZBMatrix provider')

        self.config = config

    def conf(self, option):
        return self.config.get('NZBMatrix', option)

    def enabled(self):
        return self.conf('enabled') and self.config.get('NZB', 'enabled') and self.conf('username') and self.conf('apikey')

    def find(self, movie, quality, type, retry = False):

        self.cleanCache();

        results = []
        if not self.enabled() or not self.isAvailable(self.searchUrl):
            return results

        catId = self.getCatId(type)
        arguments = urlencode({
            'term': movie.imdb,
            'subcat': catId,
            'username': self.conf('username'),
            'apikey': self.conf('apikey'),
            'searchin': 'weblink',
            'english': 1 if self.conf('english') else 0,
        })
        url = "%s?%s" % (self.searchUrl, arguments)
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
                    log.debug('No valid xml or to many requests.. You never know with %s.' % self.name)
                    return results

                for nzb in xml:

                    title = self.gettextelement(nzb, "title")
                    if 'error' in title.lower(): continue

                    id = int(self.gettextelement(nzb, "link").split('&')[0].partition('id=')[2])
                    size = self.gettextelement(nzb, "description").split('<br /><b>')[2].split('> ')[1]
                    date = str(self.gettextelement(nzb, "description").split('<br /><b>')[3].partition('Added:</b> ')[2])

                    new = self.feedItem()
                    new.id = id
                    new.type = 'nzb'
                    new.name = title
                    new.date = int(time.mktime(parse(date).timetuple()))
                    new.size = self.parseSize(size)
                    new.url = self.downloadLink(id)
                    new.detailUrl = self.detailLink(id)
                    new.content = self.gettextelement(nzb, "description")
                    new.score = self.calcScore(new, movie)
                    new.checkNZB = True

                    if new.date > time.time() - (int(self.config.get('NZB', 'retention')) * 24 * 60 * 60):
                        if self.isCorrectMovie(new, movie, type, imdbResults = True, singleCategory = singleCat):
                            results.append(new)
                            log.info('Found: %s' % new.name)
                    else:
                        log.info('Found outside retention: %s' % new.name)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from NZBMatrix.com')

        return results

    def getApiExt(self):
        return '&username=%s&apikey=%s' % (self.conf('username'), self.conf('apikey'))

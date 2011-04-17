from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import NZBProvider
from dateutil.parser import parse
from urllib import urlencode
from urllib2 import URLError
import time

log = CPLog(__name__)


class Newzbin(NZBProvider):
    searchUrl = 'https://www.newzbin.com/search/'

    formatIds = {
        2: ['scr'],
        1: ['cam'],
        4: ['tc'],
        8: ['ts'],
        1024: ['r5'],
    }
    cat_ids = [
        ([2097152], ['1080p']),
        ([524288], ['720p']),
        ([262144], ['brrip']),
        ([2], ['dvdr']),
    ]
    cat_backup_id = -1

    def __init__(self):
        addEvent('provider.nzb.search', self.search)
        addEvent('provider.yarr.search', self.search)

    def search(self, movie, quality):

        results = []
        if self.isDisabled() or not self.isAvailable(self.searchUrl):
            return results

        formatId = self.getFormatId(type)
        catId = self.getCatId(type)

        arguments = urlencode({
            'searchaction': 'Search',
            'u_url_posts_only': '0',
            'u_show_passworded': '0',
            'q_url': 'imdb.com/title/' + movie.imdb,
            'sort': 'ps_totalsize',
            'order': 'asc',
            'u_post_results_amt': '100',
            'feed': 'rss',
            'category': '6',
            'ps_rb_video_format': str(catId),
            'ps_rb_source': str(formatId),
        })

        url = "%s?%s" % (self.searchUrl, arguments)
        cacheId = str('%s %s %s' % (movie.imdb, str(formatId), str(catId)))
        singleCat = True

        try:
            cached = False
            if(self.cache.get(cacheId)):
                data = True
                cached = True
                log.info('Getting RSS from cache: %s.' % cacheId)
            else:
                log.info('Searching: %s' % url)
                data = self.urlopen(url, username = self.conf('username'), password = self.conf('password'))
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

                for item in xml:

                    title = self.gettextelement(item, "title")
                    if 'error' in title.lower(): continue

                    REPORT_NS = 'http://www.newzbin.com/DTD/2007/feeds/report/';

                    # Add attributes to name
                    for attr in item.find('{%s}attributes' % REPORT_NS):
                        title += ' ' + attr.text

                    id = int(self.gettextelement(item, '{%s}id' % REPORT_NS))
                    size = str(int(self.gettextelement(item, '{%s}size' % REPORT_NS)) / 1024 / 1024) + ' mb'
                    date = str(self.gettextelement(item, '{%s}postdate' % REPORT_NS))

                    new = self.feedItem()
                    new.id = id
                    new.type = 'nzb'
                    new.name = title
                    new.date = int(time.mktime(parse(date).timetuple()))
                    new.size = self.parseSize(size)
                    new.url = str(self.gettextelement(item, '{%s}nzb' % REPORT_NS))
                    new.detailUrl = str(self.gettextelement(item, 'link'))
                    new.content = self.gettextelement(item, "description")
                    new.score = self.calcScore(new, movie)
                    new.addbyid = True
                    new.checkNZB = False

                    if new.date > time.time() - (int(self.config.get('NZB', 'retention')) * 24 * 60 * 60) and self.isCorrectMovie(new, movie, type, imdbResults = True, singleCategory = singleCat):
                        results.append(new)
                        log.info('Found: %s' % new.name)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from newzbin.com')

        return results

    def getFormatId(self, format):
        for id, quality in self.formatIds.iteritems():
            for q in quality:
                if q == format:
                    return id

        return self.catBackupId

    def isEnabled(self):
        return NZBProvider.isEnabled(self) and self.conf('enabled') and self.conf('username') and self.conf('password')

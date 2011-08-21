from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import NZBProvider
from dateutil.parser import parse
from urllib import urlencode
from urllib2 import URLError
import time
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class NzbIndex(NZBProvider, RSS):

    urls = {
        'download': 'http://www.nzbindex.nl/download/%s/%s',
        'api': 'http://www.nzbindex.nl/rss/', #http://www.nzbindex.nl/rss/?q=due+date+720p&age=1000&sort=agedesc&minsize=3500&maxsize=10000
    }

    time_between_searches = 1 # Seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled() or not self.isAvailable(self.urls['api']):
            return results

        arguments = urlencode({
            'q': '%s %s' % (simplifyString(movie['library']['titles'][0]['title']), quality.get('identifier')),
            'sort': 'agedesc',
            'minsize': quality.get('size_min'),
            'maxsize': quality.get('size_max'),
            'rating': '1',
        })
        url = "%s?%s" % (self.urls['api'], arguments)

        cache_key = 'nzbindex.%s.%s' % (movie['library'].get('identifier'), quality.get('identifier'))

        try:
            data = self.getCache(cache_key)
            if not data:
                data = self.urlopen(url)
                self.setCache(cache_key, data)
        except (IOError, URLError):
            log.error('Failed to open %s.' % url)
            return results

        if data:
            try:
                try:
                    data = XMLTree.fromstring(data)
                    nzbs = self.getElements(data, 'channel/item')
                except Exception, e:
                    log.debug('%s, %s' % (self.getName(), e))
                    return results

                for nzb in nzbs:

                    enclosure = self.getElements(nzb, 'enclosure')[0].attrib

                    id = int(self.getTextElement(nzb, "link").split('/')[4])
                    new = {
                        'id': id,
                        'type': 'nzb',
                        'name': self.getTextElement(nzb, "title"),
                        'age': self.calculateAge(int(time.mktime(parse(self.getTextElement(nzb, "pubDate")).timetuple()))),
                        'size': enclosure['length'],
                        'url': enclosure['url'],
                        'detail_url': enclosure['url'].replace('/download/', '/release/'),
                        'description': self.getTextElement(nzb, "description"),
                        'check_nzb': True,
                    }
                    new['score'] = fireEvent('score.calculate', new, movie, single = True)

                    is_correct_movie = fireEvent('searcher.correct_movie',
                                                 nzb = new, movie = movie, quality = quality,
                                                 imdb_results = False, single_category = False, single = True)

                    if is_correct_movie:
                        results.append(new)
                        self.found(new)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from NZBMatrix.com')

        return results


    def isEnabled(self):
        return NZBProvider.isEnabled(self) and self.conf('enabled')

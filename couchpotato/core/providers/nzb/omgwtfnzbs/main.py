from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt, getTitle, possibleTitles
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from dateutil.parser import parse
from urlparse import urlparse, parse_qs
import time
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class OMGWTFNZBs(NZBProvider, RSS):

    urls = {
        'search': 'http://rss.omgwtfnzbs.com/rss-search.php?%s',
    }

    http_time_between_calls = 1 #seconds

    cat_ids = [
        ([15], ['dvdrip']),
        ([15, 16], ['brrip']),
        ([16], ['720p', '1080p', 'bd50']),
        ([17], ['dvdr']),
    ]
    cat_backup_id = 'movie'

    def search(self, movie, quality):

        pre_releases = fireEvent('quality.pre_releases', single = True)
        if self.isDisabled() or quality['identifier'] in pre_releases:
            return []

        results = []
        for title in possibleTitles(getTitle(movie['library'])):
            results.extend(self._search(title, movie, quality))

        return self.removeDuplicateResults(results)

    def _search(self, title, movie, quality):
        results = []

        q = '%s %s' % (title, movie['library']['year'])

        params = {
            'search': q,
            'catid': ','.join([str(x) for x in self.getCatId(quality['identifier'])]),
            'user': self.conf('username', default = ''),
            'api': self.conf('api_key', default = ''),
        }

        cache_key = 'omgwtfnzbs.%s.%s' % (movie['library']['identifier'], q)
        data = self.getCache(cache_key, self.urls['search'] % tryUrlencode(params))
        if data:
            try:
                try:
                    data = XMLTree.fromstring(data)
                    nzbs = self.getElements(data, 'channel/item')
                except Exception, e:
                    log.debug('%s, %s', (self.getName(), e))
                    return results

                for nzb in nzbs:

                    nzb_id = parse_qs(urlparse(self.getTextElement(nzb, "link")).query).get('id')[0]
                    enclosure = self.getElement(nzb, "enclosure").attrib
                    size = enclosure['length']
                    date = self.getTextElement(nzb, "pubDate")

                    new = {
                        'id': nzb_id,
                        'type': 'nzb',
                        'provider': self.getName(),
                        'name': toUnicode(self.getTextElement(nzb, "title")),
                        'age': self.calculateAge(int(time.mktime(parse(date).timetuple()))),
                        'size': tryInt(size) / 1024 / 1024,
                        'url': enclosure['url'],
                        'download': self.download,
                        'detail_url': self.getTextElement(nzb, "link"),
                        'description': self.getTextElement(nzb, 'description')
                    }

                    is_correct_movie = fireEvent('searcher.correct_movie',
                                                 nzb = new, movie = movie, quality = quality,
                                                 imdb_results = False, single = True)

                    if is_correct_movie:
                        new['score'] = fireEvent('score.calculate', new, movie, single = True)
                        results.append(new)
                        self.found(new)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from omgwtfnzbs')

        return results

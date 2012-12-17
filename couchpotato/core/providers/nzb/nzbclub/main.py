from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt, getTitle, possibleTitles
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from dateutil.parser import parse
import time
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class NZBClub(NZBProvider, RSS):

    urls = {
        'search': 'http://www.nzbclub.com/nzbfeed.aspx?%s',
    }

    http_time_between_calls = 4 #seconds

    def search(self, movie, quality):

        if self.isDisabled():
            return []

        results = []
        for title in possibleTitles(getTitle(movie['library'])):
            results.extend(self._search(title, movie, quality))

        return self.removeDuplicateResults(results)

    def _search(self, title, movie, quality):
        results = []

        q = '"%s %s" %s' % (title, movie['library']['year'], quality.get('identifier'))

        params = {
            'q': q,
            'ig': '1',
            'rpp': 200,
            'st': 1,
            'sp': 1,
            'ns': 1,
        }

        cache_key = 'nzbclub.%s.%s.%s' % (movie['library']['identifier'], quality.get('identifier'), q)
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

                    nzbclub_id = tryInt(self.getTextElement(nzb, "link").split('/nzb_view/')[1].split('/')[0])
                    enclosure = self.getElement(nzb, "enclosure").attrib
                    size = enclosure['length']
                    date = self.getTextElement(nzb, "pubDate")

                    def extra_check(item):
                        full_description = self.getCache('nzbclub.%s' % nzbclub_id, item['detail_url'], cache_timeout = 25920000)

                        for ignored in ['ARCHIVE inside ARCHIVE', 'Incomplete', 'repair impossible']:
                            if ignored in full_description:
                                log.info('Wrong: Seems to be passworded or corrupted files: %s', new['name'])
                                return False

                        return True

                    new = {
                        'id': nzbclub_id,
                        'type': 'nzb',
                        'provider': self.getName(),
                        'name': toUnicode(self.getTextElement(nzb, "title")),
                        'age': self.calculateAge(int(time.mktime(parse(date).timetuple()))),
                        'size': tryInt(size) / 1024 / 1024,
                        'url': enclosure['url'].replace(' ', '_'),
                        'download': self.download,
                        'detail_url': self.getTextElement(nzb, "link"),
                        'description': '',
                        'get_more_info': self.getMoreInfo,
                        'extra_check': extra_check
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
                log.error('Failed to parse XML response from NZBClub')

        return results

    def getMoreInfo(self, item):
        full_description = self.getCache('nzbclub.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('pre', attrs = {'class':'nfo'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

    def extraCheck(self, item):
        full_description = self.getCache('nzbclub.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)

        if 'ARCHIVE inside ARCHIVE' in full_description:
            log.info('Wrong: Seems to be passworded files: %s', item['name'])
            return False

        return True

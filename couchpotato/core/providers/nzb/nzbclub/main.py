from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
from dateutil.parser import parse
import time
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class NZBClub(NZBProvider, RSS):

    urls = {
        'search': 'https://www.nzbclub.com/nzbfeed.aspx?%s',
    }

    http_time_between_calls = 3 #seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled() or not self.isAvailable(self.urls['search']):
            return results

        q = '"%s" %s %s' % (movie['library']['titles'][0]['title'], movie['library']['year'], quality.get('identifier'))
        for ignored in Env.setting('ignored_words', 'searcher').split(','):
            q = '%s -%s' % (q, ignored.strip())

        params = {
            'q': q,
            'ig': '1',
            'rpp': 200,
            'st': 1,
            'sp': 1,
            'ns': 1,
        }

        cache_key = 'nzbclub.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
        data = self.getCache(cache_key, self.urls['search'] % tryUrlencode(params))
        if data:
            try:
                try:
                    data = XMLTree.fromstring(data)
                    nzbs = self.getElements(data, 'channel/item')
                except Exception, e:
                    log.debug('%s, %s' % (self.getName(), e))
                    return results

                for nzb in nzbs:

                    nzbclub_id = tryInt(self.getTextElement(nzb, "link").split('/nzb_view/')[1].split('/')[0])
                    enclosure = self.getElement(nzb, "enclosure").attrib
                    size = enclosure['length']
                    date = self.getTextElement(nzb, "pubDate")

                    description = toUnicode(self.getCache('nzbclub.%s' % nzbclub_id, self.getTextElement(nzb, "link"), timeout = 25920000))

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
                        'description': description,
                    }
                    new['score'] = fireEvent('score.calculate', new, movie, single = True)

                    if 'ARCHIVE inside ARCHIVE' in description:
                        log.info('Wrong: Seems to be passworded files: %s' % new['name'])
                        continue

                    is_correct_movie = fireEvent('searcher.correct_movie',
                                                 nzb = new, movie = movie, quality = quality,
                                                 imdb_results = False, single_category = False, single = True)

                    if is_correct_movie:
                        results.append(new)
                        self.found(new)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from NZBClub')

        return results

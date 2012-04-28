from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
from dateutil.parser import parse
import re
import time
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class NzbIndex(NZBProvider, RSS):

    urls = {
        'download': 'http://www.nzbindex.nl/download/',
        'api': 'http://www.nzbindex.nl/rss/',
    }

    http_time_between_calls = 1 # Seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled() or not self.isAvailable(self.urls['api']):
            return results

        q = '%s %s %s' % (movie['library']['titles'][0]['title'], movie['library']['year'], quality.get('identifier'))
        arguments = tryUrlencode({
            'q': q,
            'age': Env.setting('retention', 'nzb'),
            'sort': 'agedesc',
            'minsize': quality.get('size_min'),
            'maxsize': quality.get('size_max'),
            'rating': 1,
            'max': 250,
            'more': 1,
            'complete': 1,
        })
        url = "%s?%s" % (self.urls['api'], arguments)

        cache_key = 'nzbindex.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))

        data = self.getCache(cache_key, url)
        if data:
            try:
                try:
                    data = XMLTree.fromstring(data)
                    nzbs = self.getElements(data, 'channel/item')
                except Exception, e:
                    log.debug('%s, %s' % (self.getName(), e))
                    return results

                for nzb in nzbs:

                    enclosure = self.getElement(nzb, 'enclosure').attrib

                    nzbindex_id = int(self.getTextElement(nzb, "link").split('/')[4])

                    try:
                        description = self.getTextElement(nzb, "description")
                        if ' nfo' in description.lower():
                            nfo_url = re.search('href="(?P<nfo>.+)"', description).group('nfo')
                            description = toUnicode(self.getCache('nzbindex.%s' % nzbindex_id, nfo_url, timeout = 25920000))
                    except:
                        pass

                    new = {
                        'id': nzbindex_id,
                        'type': 'nzb',
                        'provider': self.getName(),
                        'name': self.getTextElement(nzb, "title"),
                        'age': self.calculateAge(int(time.mktime(parse(self.getTextElement(nzb, "pubDate")).timetuple()))),
                        'size': tryInt(enclosure['length']) / 1024 / 1024,
                        'url': enclosure['url'],
                        'detail_url': enclosure['url'].replace('/download/', '/release/'),
                        'description': description,
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

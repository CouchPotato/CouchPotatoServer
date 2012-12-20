from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
import json
import traceback

log = CPLog(__name__)


class Nzbx(NZBProvider, RSS):
    endpoint = 'https://nzbx.co/api/'

    urls = {
        'search': 'https://nzbx.co/api/search',
        'details': 'https://nzbx.co/api/details?guid=%s',
        'comments': 'https://nzbx.co/api/get-comments?guid=%s',
        'ratings': 'https://nzbx.co/api/get-votes?guid=%s',
        'downloads': 'https://nzbx.co/api/get-downloads-count?guid=%s',
        'categories': 'https://nzbx.co/api/categories',
        'groups': 'https://nzbx.co/api/groups',
    }

    http_time_between_calls = 1 # Seconds

    def search(self, movie, quality):
        results = []

        if self.isDisabled():
            return results

        arguments = tryUrlencode({
            'q': movie['library']['identifier'].replace('tt', ''),
            'sf': quality.get('size_min'),
        })
        url = "%s?%s" % (self.urls['search'], arguments)

        cache_key = 'nzbx.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))

        data = self.getCache(cache_key, url)

        if data:
            try:
                try:
                    nzbs = json.loads(data)
                except Exception, e:
                    log.debug('%s, %s', (self.getName(), e))
                    return results

                for nzb in nzbs:

                    nzbx_guid = nzb['guid']

                    def extra_score(item):
                        score = 0
                        if item['votes']['upvotes'] > item['votes']['downvotes']:
                            score += 5
                        return score

                    new = {
                        'guid': nzbx_guid,
                        'type': 'nzb',
                        'provider': self.getName(),
                        'download': self.download,
                        'url': nzb['nzb'],
                        'name': nzb['name'],
                        'age': self.calculateAge(int(nzb['postdate'])),
                        'size': tryInt(nzb['size']) / 1024 / 1024,
                        'description': '',
                        'extra_score': extra_score,
                        'votes': nzb['votes'],
                        'check_nzb': True,
                    }

                    is_correct_movie = fireEvent('searcher.correct_movie',
                                                 nzb = new, movie = movie, quality = quality,
                                                 imdb_results = False, single = True)

                    if is_correct_movie:
                        new['score'] = fireEvent('score.calculate', new, movie, single = True)
                        results.append(new)
                        self.found(new)

                return results
            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

        return results


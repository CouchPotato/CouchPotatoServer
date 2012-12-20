from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode, \
    simplifyString
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
from dateutil.parser import parse
import re
import time
import traceback
import json

log = CPLog(__name__)


class Nzbx(NZBProvider, RSS):
	endpoint = 'https://nzbx.co/api/'
	
    urls = {
        'search': endpoint + 'search',
		'details': endpoint + 'details?guid=%s',
		'comments': endpoint + 'get-comments?guid=%s',
		'ratings': endpoint + 'get-votes?guid=%s',
		'downloads': endpoint + 'get-downloads-count?guid=%s',
		'categories': endpoint + 'categories',
		'groups': endpoint + 'groups',
    }

    http_time_between_calls = 1 # Seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        q = '"%s %s" %s' % (simplifyString(getTitle(movie['library'])), movie['library']['year'], quality.get('identifier'))
        arguments = tryUrlencode({
            'q': q,
			'l': 250, # Limit on number of files returned
			#'i': '', # index of file
			#'sf': '' # size filter
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
					
					# need to filter by completed
					
                    new = {
                        'guid': nzbx_guid,
                        'type': 'nzb',
                        'provider': self.getName(),
                        'download': nzb['nzb'],
                        'name': nzb['name'],
                        'age': self.calculateAge(int(nzb['postdate'])),
                        'size': tryInt(nzb['size']) / 1024 / 1024,
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

    def isEnabled(self):
        return NZBProvider.isEnabled(self) and self.conf('enabled')

from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from dateutil.parser import parse
import re
import time

log = CPLog(__name__)


class Moovee(NZBProvider):

    urls = {
        'download': 'http://85.214.105.230/get_nzb.php?id=%s&section=moovee',
        'search': 'http://abmoovee.allfilled.com/search.php?q=%s&Search=Search',
    }

    regex = '<td class="cell_reqid">(?P<reqid>.*?)</td>.+?<td class="cell_request">(?P<title>.*?)</td>.+?<td class="cell_statuschange">(?P<age>.*?)</td>'

    http_time_between_calls = 2 # Seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled() or not self.isAvailable(self.urls['search']) or quality.get('hd', False):
            return results

        q = '%s %s' % (movie['library']['titles'][0]['title'], quality.get('identifier'))
        url = self.urls['search'] % tryUrlencode(q)

        cache_key = 'moovee.%s' % q
        data = self.getCache(cache_key, url)
        if data:
            match = re.compile(self.regex, re.DOTALL).finditer(data)

            for nzb in match:
                new = {
                    'id': nzb.group('reqid'),
                    'name': nzb.group('title'),
                    'type': 'nzb',
                    'provider': self.getName(),
                    'age': self.calculateAge(time.mktime(parse(nzb.group('age')).timetuple())),
                    'size': None,
                    'url': self.urls['download'] % (nzb.group('reqid')),
                    'detail_url': '',
                    'description': '',
                    'check_nzb': False,
                }

                new['score'] = fireEvent('score.calculate', new, movie, single = True)
                is_correct_movie = fireEvent('searcher.correct_movie',
                                                    nzb = new, movie = movie, quality = quality,
                                                    imdb_results = False, single_category = False, single = True)
                if is_correct_movie:
                    results.append(new)
                    self.found(new)

        return results

    def belongsTo(self, url, host = None):
        match = re.match('http://85\.214\.105\.230/get_nzb\.php\?id=[0-9]*&section=moovee', url)
        if match:
            return self
        return

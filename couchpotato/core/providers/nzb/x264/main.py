from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
import re

log = CPLog(__name__)


class X264(NZBProvider):

    urls = {
        'download': 'http://85.214.105.230/get_nzb.php?id=%s&section=hd',
        'search': 'http://85.214.105.230/x264/requests.php?release=%s&status=FILLED&age=1300&sort=ID',
    }

    regex = '<tr class="req_filled"><td class="reqid">(?P<id>.*?)</td><td class="release">(?P<title>.*?)</td>.+?<td class="age">(?P<age>.*?)</td>'

    http_time_between_calls = 2 # Seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled() or not self.isAvailable(self.urls['search'].split('requests')[0]) or not quality.get('hd', False):
            return results

        q = '%s %s %s' % (getTitle(movie['library']), movie['library']['year'], quality.get('identifier'))
        url = self.urls['search'] % tryUrlencode(q)

        cache_key = 'x264.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
        data = self.getCache(cache_key, url)
        if data:
            match = re.compile(self.regex, re.DOTALL).finditer(data)

            for nzb in match:
                try:
                    age_match = re.match('((?P<day>\d+)d)', nzb.group('age'))
                    age = age_match.group('day')
                except:
                    age = 1

                new = {
                    'id': nzb.group('id'),
                    'name': nzb.group('title'),
                    'type': 'nzb',
                    'provider': self.getName(),
                    'age': tryInt(age),
                    'size': None,
                    'url': self.urls['download'] % (nzb.group('id')),
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
        match = re.match('http://85\.214\.105\.230/get_nzb\.php\?id=[0-9]*&section=hd', url)
        if match:
            return self
        return

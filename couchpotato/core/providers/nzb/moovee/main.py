from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from dateutil.parser import parse
from urllib import quote_plus
import re
import time

log = CPLog(__name__)


class Moovee(NZBProvider, RSS):

    urls = {
        'download': 'http://85.214.105.230/get_nzb.php?id=%s&section=moovee',
        'search': 'http://abmoovee.allfilled.com/search.php?q=%s&Search=Search',
        'regex': '<td class="cell_reqid">(?P<reqid>.*?)</td>.+?<td class="cell_request">(?P<title>.*?)</td>.+?<td class="cell_statuschange">(?P<age>.*?)</td>',
    }

    def search(self, movie, quality):

        results = []
        if self.isDisabled() or not self.isAvailable(self.urls['search']):
            return results

        url = self.urls['search'] % quote_plus(movie['library']['titles'][0]['title'] + ' ' + quality.get('identifier'))
        log.info('Searching: %s' % url)

        data = self.urlopen(url)
        match = re.compile(self.urls['regex'], re.DOTALL).finditer(data)

        for nzb in match:
            new = {
                'id': nzb.group('reqid'),
                'name': nzb.group('title'),
                'type': 'nzb',
                'provider': self.getName(),
                'age': self.calculateAge(time.mktime(parse(nzb.group('age')).timetuple())),
                'size': None,
                'url': self.urls['download'] % (nzb.group('reqid')),
                'download': self.download,
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

    def download(self, url = '', nzb_id = ''):
        try:
            log.info('Downloading nzb from #alt.binaries.moovee, request id: %s ' % nzb_id)
            return self.urlopen(self.urls['download'] % nzb_id)

        except Exception, e:
            log.error('Failed downloading from #alt.binaries.moovee: %s' % e)
            return False

    def belongsTo(self, url, host = None):
        match = re.match('http://85\.214\.105\.230/get_nzb\.php\?id=[0-9]*&section=moovee', url)
        if match:
            return self
        return

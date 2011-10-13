from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from urllib import quote_plus
from dateutil.parser import parse
import re
import time

log = CPLog(__name__)


class X264(NZBProvider, RSS):

    urls = {
        'download': 'http://85.214.105.230/get_nzb.php?id=%s&section=hd',
        'search': 'http://85.214.105.230/x264/requests.php?release=%s&status=FILLED&age=700&sort=ID',
        'regex': '<tr class="req_filled"><td class="reqid">(?P<id>.*?)</td><td class="release">(?P<title>.*?)</td>.+?<td class="age">(?P<age>.*?)</td>',
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
            age = nzb.group('age')
            if "d" not in age:
                age = 1
            else:
                age = re.sub('d.*','', age)
            new = {
                'id': nzb.group('id'),
                'name': nzb.group('title'),
                'type': 'nzb',
                'provider': self.getName(),
                'age': tryInt(age),
                'size': None,
                'url': self.urls['download'] % (nzb.group('id')),
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
            log.info('Downloading nzb from #alt.binaries.hdtv.x264, request id: %s ' % nzb_id)
            return self.urlopen(self.urls['download'] % nzb_id)

        except Exception, e:
            log.error('Failed downloading from #alt.binaries.hdtv.x264: %s' % e)
            return False

    def belongsTo(self, url, host = None):
        match = re.match('http://85\.214\.105\.230/get_nzb\.php\?id=[0-9]*&section=hd', url)
        if match:
            return self
        return
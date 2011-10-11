from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from dateutil.parser import parse
from imdb.parser.http.bsouplxml._bsoup import SoupStrainer, BeautifulSoup
import urllib
import urllib2
from urllib import urlencode
from urllib import quote_plus
import time
import re

log = CPLog(__name__)


class X264(NZBProvider, RSS):

    urls = {
        'download': 'http://85.214.105.230/get_nzb.php?id=%s&section=hd',
        'search': 'http://85.214.105.230/x264/requests.php?release=%s&status=FILLED&age=700&sort=ID',
        'regex': '<tr class="req_filled"><td class="reqid">(?P<id>.*?)</td><td class="release">(?P<title>.*?)</td>',
    }

    def search(self, movie, quality):

        results = []
        if self.isDisabled() or not self.isAvailable(self.urls['search']):
            return results

        url = self.urls['search'] % quote_plus(movie['library']['titles'][0]['title'] + ' ' + quality.get('identifier'))
        log.info('Searching: %s' % url)

        try:
           opener = urllib2.build_opener()
           urllib2.install_opener(opener)
           f = opener.open(url)
           data = f.read()
           f.close()

        except (IOError, URLError):
            log.error('Failed to open %s.' % url)
            return results

        match = re.compile(self.urls['regex'], re.DOTALL ).finditer(data)

        for nzb in match:
             new = {
                     'id': nzb.group('id'),
                     'name': nzb.group('title'),
                     'type': 'nzb',
                     'provider': self.getName(),
                     'age': self.calculateAge(time.time()),
                     'size': 9999,
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
            log.info('Download nzb from #alt.binaries.hdtv.x264, report id: %s ' % nzb_id)

            return self.urlopen(self.urls['download'] % nzb_id)
        except Exception, e:
            log.error('Failed downloading from #alt.binaries.hdtv.x264, check credit: %s' % e)
            return False

    def getFormatId(self, format):
        for id, quality in self.format_ids.iteritems():
            for q in quality:
                if q == format:
                    return id

        return self.cat_backup_id

    def isEnabled(self):
        return NZBProvider.isEnabled(self) and self.conf('enabled')

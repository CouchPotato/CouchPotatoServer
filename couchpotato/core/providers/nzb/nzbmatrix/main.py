from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
from dateutil.parser import parse
from urllib import urlencode
import time
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class NZBMatrix(NZBProvider, RSS):

    urls = {
        'download': 'https://api.nzbmatrix.com/v1.1/download.php?id=%s',
        'detail': 'https://nzbmatrix.com/nzb-details.php?id=%s&hit=1',
        'search': 'http://rss.nzbmatrix.com/rss.php',
    }

    cat_ids = [
        ([50], ['blu']),
        ([42, 53], ['720p', '1080p']),
        ([2], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr']),
        ([54], ['brrip']),
        ([1], ['dvdr']),
    ]
    cat_backup_id = 2

    def search(self, movie, quality):

        results = []

        if self.isDisabled() or not self.isAvailable(self.urls['search']):
            return results

        cat_ids = ','.join(['%s' % x for x in self.getCatId(quality.get('identifier'))])

        arguments = urlencode({
            'term': movie['library']['identifier'],
            'subcat': cat_ids,
            'username': self.conf('username'),
            'apikey': self.conf('api_key'),
            'searchin': 'weblink',
            'age': Env.setting('retention', section = 'nzb'),
            'english': self.conf('english_only'),
        })
        url = "%s?%s" % (self.urls['search'], arguments)

        cache_key = 'nzbmatrix.%s.%s' % (movie['library'].get('identifier'), cat_ids)
        single_cat = True

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

                    title = self.getTextElement(nzb, "title")
                    if 'error' in title.lower(): continue

                    id = int(self.getTextElement(nzb, "link").split('&')[0].partition('id=')[2])
                    size = self.getTextElement(nzb, "description").split('<br /><b>')[2].split('> ')[1]
                    date = str(self.getTextElement(nzb, "description").split('<br /><b>')[3].partition('Added:</b> ')[2])

                    new = {
                        'id': id,
                        'type': 'nzb',
                        'provider': self.getName(),
                        'name': title,
                        'age': self.calculateAge(int(time.mktime(parse(date).timetuple()))),
                        'size': self.parseSize(size),
                        'url': self.urls['download'] % id + self.getApiExt(),
                        'download': self.download,
                        'detail_url': self.urls['detail'] % id,
                        'description': self.getTextElement(nzb, "description"),
                        'check_nzb': True,
                    }
                    new['score'] = fireEvent('score.calculate', new, movie, single = True)

                    is_correct_movie = fireEvent('searcher.correct_movie',
                                                 nzb = new, movie = movie, quality = quality,
                                                 imdb_results = True, single_category = single_cat, single = True)

                    if is_correct_movie:
                        results.append(new)
                        self.found(new)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from NZBMatrix.com')

        return results

    def getApiExt(self):
        return '&username=%s&apikey=%s' % (self.conf('username'), self.conf('api_key'))

    def isEnabled(self):
        return NZBProvider.isEnabled(self) and self.conf('username') and self.conf('api_key')

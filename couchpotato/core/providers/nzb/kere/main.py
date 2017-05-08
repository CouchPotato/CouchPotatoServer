from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
from libs.dateutil.parser import parse
import time
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class Kere(NZBProvider, RSS):

    urls = {
        'download': 'http://kere.ws/api?t=get&id=%s',
        'detail': 'http://kere.ws/api?t=details&id=%s',
        'search': 'http://kere.ws/api',
    }

    cat_ids = [
        ([1000], [ 'cam', 'ts', 'tc', 'scr']),
		([1010], [ 'r5' ]),
		([1020], [ 'dvdrip', 'brrip' ]),
		([1030], [ 'dvdr' ]),
		([1050], [ '720p' ]),
		([1060], [ '1080p' ]),
    ]
    cat_backup_id = 2

    def search(self, movie, quality):

        results = []

        if self.isDisabled():
            return results

        cat_ids = ','.join(['%s' % x for x in self.getCatId(quality.get('identifier'))])

        arguments = tryUrlencode({
            't' : 'movie',
            'imdbid': movie['library']['identifier'].replace('tt',''),
            'cat': cat_ids,
            'apikey': self.conf('api_key'),
        })
        url = "%s?%s" % (self.urls['search'], arguments)

        cache_key = 'kere.%s.%s' % (movie['library'].get('identifier'), cat_ids)
        
        data = self.getCache(cache_key, url, cache_timeout = 1800, headers = {'User-Agent': Env.getIdentifier()})
        if data:
            try:
                try:
                    data = XMLTree.fromstring(data)
                    nzbs = self.getElements(data, 'channel/item')
                except Exception, e:
                    log.debug('%s, %s', (self.getName(), e))
                    return results

                for nzb in nzbs:

                    title = self.getTextElement(nzb, "title")
                    if 'error' in title.lower(): continue

                    id = self.getTextElement(nzb, "link").replace('http://kere.ws/getnzb/','').split('.')[0]
                    size = '%f KB' % (float(str(nzb.find('enclosure').attrib).split("'length': ")[1].split(',')[0].strip("'").strip()) / 1024)
                    date = str(self.getTextElement(nzb, "pubDate"))

                    new = {
                        'id': str(id),
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

                    is_correct_movie = fireEvent('searcher.correct_movie',
                                                 nzb = new, movie = movie, quality = quality,
                                                 imdb_results = True, single = True)

                    if is_correct_movie:
                        new['score'] = fireEvent('score.calculate', new, movie, single = True)
                        results.append(new)
                        self.found(new)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from Kere.ws')

        return results

    def download(self, url = '', nzb_id = ''):
        return self.urlopen(url, headers = {'User-Agent': Env.getIdentifier()})

    def getApiExt(self):
        return '&username=%s&apikey=%s' % (self.conf('username'), self.conf('api_key'))

    def isEnabled(self):
        return NZBProvider.isEnabled(self) and self.conf('username') and self.conf('api_key')
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from dateutil.parser import parse
import time
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class Nzbs(NZBProvider, RSS):

    urls = {
        'download': 'http://nzbs.org/index.php?action=getnzb&nzbid=%s%s',
        'nfo': 'http://nzbs.org/index.php?action=view&nzbid=%s&nfo=1',
        'detail': 'http://nzbs.org/index.php?action=view&nzbid=%s',
        'api': 'http://nzbs.org/rss.php',
    }

    cat_ids = [
        ([4], ['720p', '1080p']),
        ([2], ['cam', 'ts', 'dvdrip', 'tc', 'brrip', 'r5', 'scr']),
        ([9], ['dvdr']),
    ]
    cat_backup_id = 't2'

    http_time_between_calls = 3 # Seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled() or not self.isAvailable(self.urls['api'] + '?test' + self.getApiExt()):
            return results

        cat_id = self.getCatId(quality.get('identifier'))
        arguments = tryUrlencode({
            'action':'search',
            'q': simplifyString(movie['library']['titles'][0]['title']),
            'catid': cat_id[0],
            'i': self.conf('id'),
            'h': self.conf('api_key'),
        })
        url = "%s?%s" % (self.urls['api'], arguments)

        cache_key = 'nzbs.%s.%s' % (movie['library'].get('identifier'), str(cat_id))

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

                    id = int(self.getTextElement(nzb, "link").partition('nzbid=')[2])
                    new = {
                        'id': id,
                        'type': 'nzb',
                        'provider': self.getName(),
                        'name': self.getTextElement(nzb, "title"),
                        'age': self.calculateAge(int(time.mktime(parse(self.getTextElement(nzb, "pubDate")).timetuple()))),
                        'size': self.parseSize(self.getTextElement(nzb, "description").split('</a><br />')[1].split('">')[1]),
                        'url': self.urls['download'] % (id, self.getApiExt()),
                        'download': self.download,
                        'detail_url': self.urls['detail'] % id,
                        'description': self.getTextElement(nzb, "description"),
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
        return NZBProvider.isEnabled(self) and self.conf('enabled') and self.conf('id') and self.conf('api_key')

    def getApiExt(self):
        return '&i=%s&h=%s' % (self.conf('id'), self.conf('api_key'))

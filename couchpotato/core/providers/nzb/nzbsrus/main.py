from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
import time
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)

# See the api http://www.nzbsrus.com/NzbsrusAPI.pdf
class Nzbsrus(NZBProvider, RSS):

    urls = {
        'download': 'https://www.nzbsrus.com/nzbdownload_rss.php/%s',
        'detail': 'https://www.nzbsrus.com/nzbdetails.php?id=%s',
        'search': 'https://www.nzbsrus.com/api.php?extended=1&xml=1&listname={date,grabs}',
    }

    cat_ids = [
        ([90,45,51], ['720p', '1080p','brrip','bd50','dvdr']),
        ([48,51], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr']),



    ]
    cat_backup_id = 240

    def search(self, movie, quality):

        results = []

        if self.isDisabled():
            return results

        cat_id_string = '&'.join(['c%s=1' % x for x in self.getCatId(quality.get('identifier'))])

        arguments = tryUrlencode({
            'searchtext': 'imdb:'+movie['library']['identifier'][2:],
            'uid': self.conf('userid'),
            'key': self.conf('api_key'),
            'age': Env.setting('retention', section = 'nzb'),

        })
        # check for english_only
        if self.conf('english_only'):
            arguments += "&lang0=1&lang3=1&lang1=1"

        url = "%s&%s&%s" % (self.urls['search'], arguments ,cat_id_string)

        cache_key = 'nzbsrus_1.%s.%s' % (movie['library'].get('identifier'), cat_id_string)
        single_cat = True

        data = self.getCache(cache_key, url, cache_timeout = 1800, headers = {'User-Agent': Env.getIdentifier()})
        if data:
            try:
                try:
                    data = XMLTree.fromstring(data)
                    nzbs = self.getElements(data, 'results/result')
                except Exception, e:
                    log.debug('%s, %s', (self.getName(), e))
                    return results

                for nzb in nzbs:

                    title = self.getTextElement(nzb, "name")
                    if 'error' in title.lower(): continue

                    id = self.getTextElement(nzb, "id")
                    size = int(round(int(self.getTextElement(nzb, "size")) / 1048576))
                    age  = int(round(( time.time() - int(self.getTextElement(nzb, "postdate")) ) / 86400 ))

                  
                    new = {
                        'id': id,
                        'type': 'nzb',
                        'provider': self.getName(),
                        'name': title,
                        'age': age,
                        'size': size,
                        'url': self.urls['download'] % id + self.getApiExt() + self.getTextElement(nzb, "key"),
                        'download': self.download,
                        'detail_url': self.urls['detail'] % id,
                        'description': self.getTextElement(nzb, "addtext"),
                        'check_nzb': True,
                    }

                    is_correct_movie = fireEvent('searcher.correct_movie',
                                                 nzb = new, movie = movie, quality = quality,
                                                 imdb_results = True, single_category = single_cat, single = True)

                    if is_correct_movie:
                        new['score'] = fireEvent('score.calculate', new, movie, single = True)
                        results.append(new)
                        self.found(new)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from Nzbsrus.com')

        return results

    def download(self, url = '', nzb_id = ''):
        return self.urlopen(url, headers = {'User-Agent': Env.getIdentifier()})

    def getApiExt(self):
        return '/%s/' % (self.conf('userid'))

    def isEnabled(self):
        return NZBProvider.isEnabled(self) and self.conf('userid') and self.conf('api_key')

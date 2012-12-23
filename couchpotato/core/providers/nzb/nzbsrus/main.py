from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import ResultList
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
import time

log = CPLog(__name__)

class Nzbsrus(NZBProvider, RSS):

    urls = {
        'download': 'https://www.nzbsrus.com/nzbdownload_rss.php/%s',
        'detail': 'https://www.nzbsrus.com/nzbdetails.php?id=%s',
        'search': 'https://www.nzbsrus.com/api.php?extended=1&xml=1&listname={date,grabs}',
    }

    cat_ids = [
        ([90, 45, 51], ['720p', '1080p', 'brrip', 'bd50', 'dvdr']),
        ([48, 51], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr']),
    ]
    cat_backup_id = 240

    def search(self, movie, quality):

        if self.isDisabled():
            return []

        results = ResultList(self, movie, quality, imdb_result = True)

        cat_id_string = '&'.join(['c%s=1' % x for x in self.getCatId(quality.get('identifier'))])
        arguments = tryUrlencode({
            'searchtext': 'imdb:' + movie['library']['identifier'][2:],
            'uid': self.conf('userid'),
            'key': self.conf('api_key'),
            'age': Env.setting('retention', section = 'nzb'),

        })

        # check for english_only
        if self.conf('english_only'):
            arguments += '&lang0=1&lang3=1&lang1=1'

        url = '%s&%s&%s' % (self.urls['search'], arguments , cat_id_string)
        nzbs = self.getRSSData(url, cache_timeout = 1800, headers = {'User-Agent': Env.getIdentifier()})

        for nzb in nzbs:

            title = self.getTextElement(nzb, 'name')
            if 'error' in title.lower(): continue

            nzb_id = self.getTextElement(nzb, 'id')
            size = int(round(int(self.getTextElement(nzb, 'size')) / 1048576))
            age = int(round((time.time() - int(self.getTextElement(nzb, 'postdate'))) / 86400))

            results.append({
                'id': nzb_id,
                'name': title,
                'age': age,
                'size': size,
                'url': self.urls['download'] % id + self.getApiExt() + self.getTextElement(nzb, 'key'),
                'detail_url': self.urls['detail'] % nzb_id,
                'description': self.getTextElement(nzb, 'addtext'),
            })

        return results

    def getApiExt(self):
        return '/%s/' % (self.conf('userid'))

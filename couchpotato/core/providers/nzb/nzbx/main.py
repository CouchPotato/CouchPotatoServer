from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider

log = CPLog(__name__)


class Nzbx(NZBProvider):

    urls = {
        'search': 'https://nzbx.co/api/search?%s',
        'details': 'https://nzbx.co/api/details?guid=%s',
    }

    http_time_between_calls = 1 # Seconds

    def _search(self, movie, quality, results):

        # Get nbzs
        arguments = tryUrlencode({
            'q': movie['library']['identifier'].replace('tt', ''),
            'sf': quality.get('size_min'),
        })
        nzbs = self.getJsonData(self.urls['search'] % arguments)

        for nzb in nzbs:

            results.append({
                'id': nzb['guid'],
                'url': nzb['nzb'],
                'detail_url': self.urls['details'] % nzb['guid'],
                'name': nzb['name'],
                'age': self.calculateAge(int(nzb['postdate'])),
                'size': tryInt(nzb['size']) / 1024 / 1024,
                'score': 5 if nzb['votes']['upvotes'] > nzb['votes']['downvotes'] else 0
            })

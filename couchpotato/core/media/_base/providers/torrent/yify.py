import traceback

from couchpotato.core.helpers.variable import tryInt, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentMagnetProvider


log = CPLog(__name__)


class Base(TorrentMagnetProvider):

    urls = {
        'test': '%s/api',
        'search': '%s/api/list.json?keywords=%s',
        'detail': '%s/api/movie.json?id=%s'
    }

    http_time_between_calls = 1  # seconds

    proxy_list = [
        'https://yts.re',
        'http://ytsproxy.come.in',
        'http://yts.im',
        'http://yify-torrents.im',
    ]

    def search(self, movie, quality):

        if not quality.get('hd', False):
            return []

        return super(Base, self).search(movie, quality)

    def _search(self, movie, quality, results):

        domain = self.getDomain()
        if not domain:
            return

        search_url = self.urls['search'] % (domain, getIdentifier(movie))

        data = self.getJsonData(search_url)

        if data and data.get('MovieList'):
            try:
                for result in data.get('MovieList'):

                    if result['Quality'] and result['Quality'] not in result['MovieTitle']:
                        title = result['MovieTitle'] + ' BrRip ' + result['Quality']
                    else:
                        title = result['MovieTitle'] + ' BrRip'

                    results.append({
                        'id': result['MovieID'],
                        'name': title,
                        'url': result['TorrentMagnetUrl'],
                        'detail_url': self.urls['detail'] % (domain, result['MovieID']),
                        'size': self.parseSize(result['Size']),
                        'seeders': tryInt(result['TorrentSeeds']),
                        'leechers': tryInt(result['TorrentPeers']),
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def correctProxy(self, data):
        data = data.lower()
        return 'yify' in data and 'yts' in data


config = [{
    'name': 'yify',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'Yify',
            'description': 'Free provider, less accurate. Small HD movies, encoded by <a href="https://yify-torrents.com/">Yify</a>.',
            'wizard': False,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAACL0lEQVR4AS1SPW/UQBAd23fxne/Ld2dvzvHuzPocEBAKokCBqGiQ6IgACYmvUKRBFEQgKKGg4BAlUoggggYUEQpSHOI7CIEoQs/fYcbLaU/efTvvvZlnA1qydoxU5kcxX0CkgmQZtPy0hCUjvK+WgEByOZ5dns1O5bzna8fRVkgsxH8B0YouIvBhdD5T11NiVOoKrsttyUcpRW0InUrFnwe9HzuP2uaQZYhF2LQ76TTXw2RVMTK8mYYbjfh+zNquMVCrqn93aArLSixPxnafdGDLaz1tjY5rmNa8z5BczEQOxQfCl1GyoqoWxYRN1bkh7ELw3q/vhP6HIL4TG9KumpjgvwuyM7OsjSj98E/vszMfZ7xvPtMaWxGO5crwIumKCR5HxDtJ0AWKGG204RfUd/3smJYqwem/Q7BTS1ZGfM4LNpVwuKAz6cMeROst0S2EwNE7GjTehO2H3dxqIpdkydat15G3F8SXBi4GlpBNlSz012L/k2+W0CLLk/jbcf13rf41yJeMQ8QWUZiHCfCA9ad+81nEKPtoS9mJOf9v0NmMJHgUT6xayheK9EIK7JJeU/AF4scDF7Y5SPlJrRcxJ+um4ibNEdObxLiIwJim+eT2AL5D9CIcnZ5zvSJi9eIlNHVVtZ831dk5svPgvjPWTq+ktWkd/kD0qtm71x+sDQe3kt6DXnM7Ct+GajmTxKlkAokWljyAKSm5oWa2w+BH4P2UuVub7eTyiGOQYapY/wEztHduSDYz5gAAAABJRU5ErkJggg==',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False
                },
                {
                    'name': 'domain',
                    'advanced': True,
                    'label': 'Proxy server',
                    'description': 'Domain for requests, keep empty to let CouchPotato pick.',
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        }
    ]
}]

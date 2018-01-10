from datetime import datetime
from couchpotato.core.helpers.variable import tryInt, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentMagnetProvider
import random

log = CPLog(__name__)


class Base(TorrentMagnetProvider):
    # Only qualities allowed: 720p/1080p/3D - the rest will fail.
    # All YTS.ag torrents are verified
    urls = {
        'detail': 'https://yts.am/api#list_movies',
        'search': 'https://yts.am/api/v2/list_movies.json?query_term=%s&limit=%s&page=%s'
    }

    def _search(self, movie, quality, results):
        limit = 10
        page = 1
        data = self.getJsonData(self.urls['search'] % (getIdentifier(movie), limit, page))

        if data:
            movie_count = tryInt(data['data']['movie_count'])

            if movie_count == 0:
                log.debug('%s - found no results', (self.getName()))
            else:

                movie_results = data['data']['movies']
                for i in range(0,len(movie_results)):
                    result = data['data']['movies'][i]
                    name = result['title']
                    year = result['year']
                    detail_url = result['url']

                    for torrent in result['torrents']:
                        t_quality = torrent['quality']

                        if t_quality in quality['label']:
                            hash = torrent['hash']
                            size = tryInt(torrent['size_bytes'] / 1048576)
                            seeders = tryInt(torrent['seeds'])
                            leechers = tryInt(torrent['peers'])
                            pubdate = torrent['date_uploaded']  # format: 2017-02-17 18:40:03
                            pubdate = datetime.strptime(pubdate, '%Y-%m-%d %H:%M:%S')
                            age = (datetime.now() - pubdate).days

                            results.append({
                                'id': random.randint(100, 9999),
                                'name': '%s (%s) %s %s %s' % (name, year, 'YTS', t_quality, 'BR-Rip'),
                                'url': self.make_magnet(hash, name),
                                'size': size,
                                'seeders': seeders,
                                'leechers': leechers,
                                'age': age,
                                'detail_url': detail_url,
                                'score': 1
                            })

        return

    def make_magnet(self, hash, name):
        url_encoded_trackers = 'udp%3A%2F%2Fopen.demonii.com%3A1337%2Fannounce&tr=%0Audp%3A%2F%2Ftracker.openbittorr' \
                               'ent.com%3A80&tr=%0Audp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=%0Audp%3A%2F%2Fglot' \
                               'orrents.pw%3A6969%2Fannounce&tr=%0Audp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannou' \
                               'nce&tr=%0Audp%3A%2F%2Ftorrent.gresille.org%3A80%2Fannounce&tr=%0Audp%3A%2F%2Fp4p.are' \
                               'nabg.com%3A1337&tr=%0Audp%3A%2F%2Ftracker.leechers-paradise.org%3A6969]'

        return 'magnet:?xt=urn:btih:%s&dn=%s&tr=%s' % (hash, name.replace(' ', '+'), url_encoded_trackers)


config = [{
    'name': 'yts',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'YTS',
            'description': '<a href="https://yts.ag/" target="_blank">YTS</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAACL0lEQVR4AS1SPW/UQBAd23fxne/Ld2dvzvHuzPocEBAKokCBqG'
                    'iQ6IgACYmvUKRBFEQgKKGg4BAlUoggggYUEQpSHOI7CIEoQs/fYcbLaU/efTvvvZlnA1qydoxU5kcxX0CkgmQZtPy0hCUjvK+W'
                    'gEByOZ5dns1O5bzna8fRVkgsxH8B0YouIvBhdD5T11NiVOoKrsttyUcpRW0InUrFnwe9HzuP2uaQZYhF2LQ76TTXw2RVMTK8mY'
                    'Ybjfh+zNquMVCrqn93aArLSixPxnafdGDLaz1tjY5rmNa8z5BczEQOxQfCl1GyoqoWxYRN1bkh7ELw3q/vhP6HIL4TG9Kumpjg'
                    'vwuyM7OsjSj98E/vszMfZ7xvPtMaWxGO5crwIumKCR5HxDtJ0AWKGG204RfUd/3smJYqwem/Q7BTS1ZGfM4LNpVwuKAz6cMeRO'
                    'st0S2EwNE7GjTehO2H3dxqIpdkydat15G3F8SXBi4GlpBNlSz012L/k2+W0CLLk/jbcf13rf41yJeMQ8QWUZiHCfCA9ad+81nE'
                    'KPtoS9mJOf9v0NmMJHgUT6xayheK9EIK7JJeU/AF4scDF7Y5SPlJrRcxJ+um4ibNEdObxLiIwJim+eT2AL5D9CIcnZ5zvSJi9e'
                    'IlNHVVtZ831dk5svPgvjPWTq+ktWkd/kD0qtm71x+sDQe3kt6DXnM7Ct+GajmTxKlkAokWljyAKSm5oWa2w+BH4P2UuVub7eTy'
                    'iGOQYapY/wEztHduSDYz5gAAAABJRU5ErkJggg==',

            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False
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
                    'name': 'info',
                    'label': 'Info',
                    'type':'bool',
                    'default':'False',
                    'description': 'YTS will only work if you set the minimum size for 720p to 500 and 1080p to 800',
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

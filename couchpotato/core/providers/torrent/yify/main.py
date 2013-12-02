from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentMagnetProvider
import traceback

log = CPLog(__name__)


class Yify(TorrentMagnetProvider):

    urls = {
        'test' : 'http://yify.ftwnet.co.uk/api',
        'search' : 'http://yify.ftwnet.co.uk/api/list.json?keywords=%s&quality=%s',
        'detail': 'http://yify.ftwnet.co.uk/api/movie.json?id=%s'
    }

    http_time_between_calls = 1 #seconds

    def search(self, movie, quality):

        if not quality.get('hd', False):
            return []

        return super(Yify, self).search(movie, quality)

    def _search(self, movie, quality, results):

        data = self.getJsonData(self.urls['search'] % (movie['library']['identifier'], quality['identifier']))

        if data and data.get('MovieList'):
            try:
                for result in data.get('MovieList'):

                    try:
                        title = result['TorrentUrl'].split('/')[-1][:-8].replace('_', '.').strip('._')
                        title = title.replace('.-.', '-')
                        title = title.replace('..', '.')
                    except:
                        continue

                    results.append({
                        'id': result['MovieID'],
                        'name': title,
                        'url': result['TorrentMagnetUrl'],
                        'detail_url': self.urls['detail'] % result['MovieID'],
                        'size': self.parseSize(result['Size']),
                        'seeders': tryInt(result['TorrentSeeds']),
                        'leechers': tryInt(result['TorrentPeers'])
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))


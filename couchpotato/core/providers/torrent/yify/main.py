from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import MultiProvider
from couchpotato.core.providers.info.base import MovieProvider
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)

class Yify(MultiProvider):

    def getTypes(self):
        return [Movie]

class Base(TorrentProvider):

    urls = {
        'test' : 'https://yify-torrents.com/api',
        'search' : 'https://yify-torrents.com/api/list.json?keywords=%s&quality=%s',
        'detail': 'https://yify-torrents.com/api/movie.json?id=%s'
    }

    http_time_between_calls = 1 #seconds

    def search(self, movie, quality):

        if not quality.get('hd', False):
            return []

        return super(Base, self).search(movie, quality)

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
                        'url': result['TorrentUrl'],
                        'detail_url': self.urls['detail'] % result['MovieID'],
                        'size': self.parseSize(result['Size']),
                        'seeders': tryInt(result['TorrentSeeds']),
                        'leechers': tryInt(result['TorrentPeers'])
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

class Movie(MovieProvider, Base):
    pass
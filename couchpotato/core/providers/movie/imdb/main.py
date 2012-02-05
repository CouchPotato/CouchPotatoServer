from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.movie.base import MovieProvider
from imdb import IMDb, helpers
from imdb._logging import setLevel
import time

log = CPLog(__name__)


class IMDB(MovieProvider):

    info_list = ('main', 'plot', 'release dates', 'taglines', 'synopsis')

    def __init__(self):

        #addEvent('movie.search', self.search)
        #addEvent('movie.info', self.getInfo)

        self.p = IMDb('http')
        setLevel('warn')

    def search(self, q, limit = 12):

        r = self.p.search_movie(q)
        print '==' * 80

        return []

    def getInfo(self, identifier = None):

        m = self.p.get_movie(identifier.replace('tt', ''), info = self.info_list)

        poster = m['cover url']
        poster_original = helpers.fullSizeCoverURL(m)

        movie_data = {
            'id': identifier,
            'titles': [m['title']],
            'original_title': m['title'],
            'rating': {
                'imdb': (m.get('rating'), m.get('votes')),
            },
            'images': {
                'poster': [poster] if poster else [],
                'poster_original': [poster_original] if poster_original else [],
            },
            'imdb': identifier,
            'runtime': m.get('runtime')[0].split(':')[1],
            'released': m.get('release dates')[0].split('::')[1],
            'year': m['year'],
            'plot': m.get('synopsis', ''),
            'tagline': m.get('taglines', '')[0],
            'genres': m.get('genres', []),
        }

        return movie_data

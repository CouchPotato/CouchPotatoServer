from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt, tryFloat
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.movie.base import MovieProvider
import json
import re
import traceback

log = CPLog(__name__)


class IMDBAPI(MovieProvider):

    urls = {
        'search': 'http://www.imdbapi.com/?%s',
        'info': 'http://www.imdbapi.com/?i=%s',
    }

    http_time_between_calls = 0

    def __init__(self):
        addEvent('movie.search', self.search)
        addEvent('movie.info', self.getInfo)

    def search(self, q, limit = 12):

        name_year = fireEvent('scanner.name_year', q, single = True)

        if not q or not name_year or (name_year and not name_year.get('name')):
            return []

        cache_key = 'imdbapi.cache.%s' % q
        cached = self.getCache(cache_key, self.urls['search'] % tryUrlencode({'t': name_year.get('name'), 'y': name_year.get('year', '')}), timeout = 3)

        if cached:
            result = self.parseMovie(cached)
            if result.get('titles') and len(result.get('titles')) > 0:
                log.info('Found: %s', result['titles'][0] + ' (' + str(result['year']) + ')')
                return [result]

            return []

        return []

    def getInfo(self, identifier = None):

        if not identifier:
            return {}

        cache_key = 'imdbapi.cache.%s' % identifier
        cached = self.getCache(cache_key, self.urls['info'] % identifier, timeout = 3)

        if cached:
            result = self.parseMovie(cached)
            if result.get('titles') and len(result.get('titles')) > 0:
                log.info('Found: %s', result['titles'][0] + ' (' + str(result['year']) + ')')
                return result

        return {}

    def parseMovie(self, movie):

        movie_data = {}
        try:

            try:
                if isinstance(movie, (str, unicode)):
                    movie = json.loads(movie)
            except ValueError:
                log.info('No proper json to decode')
                return movie_data

            if movie.get('Response') == 'Parse Error' or movie.get('Response') == 'False':
                return movie_data

            tmp_movie = movie.copy()
            for key in tmp_movie:
                if tmp_movie.get(key).lower() == 'n/a':
                    del movie[key]

            year = tryInt(movie.get('Year', ''))

            movie_data = {
                'via_imdb': True,
                'titles': [movie.get('Title')] if movie.get('Title') else [],
                'original_title': movie.get('Title', ''),
                'images': {
                    'poster': [movie.get('Poster', '')] if movie.get('Poster') and len(movie.get('Poster', '')) > 4 else [],
                },
                'rating': {
                    'imdb': (tryFloat(movie.get('imdbRating', 0)), tryInt(movie.get('imdbVotes', '').replace(',', ''))),
                    #'rotten': (tryFloat(movie.get('tomatoRating', 0)), tryInt(movie.get('tomatoReviews', '').replace(',', ''))),
                },
                'imdb': str(movie.get('imdbID', '')),
                'runtime': self.runtimeToMinutes(movie.get('Runtime', '')),
                'released': movie.get('Released', ''),
                'year': year if isinstance(year, (int)) else None,
                'plot': movie.get('Plot', ''),
                'genres': movie.get('Genre', '').split(','),
                'directors': movie.get('Director', '').split(','),
                'writers': movie.get('Writer', '').split(','),
                'actors': movie.get('Actors', '').split(','),
            }
        except:
            log.error('Failed parsing IMDB API json: %s', traceback.format_exc())

        return movie_data

    def runtimeToMinutes(self, runtime_str):
        runtime = 0

        regex = '(\d*.?\d+).(h|hr|hrs|mins|min)+'
        matches = re.findall(regex, runtime_str)
        for match in matches:
            nr, size = match
            runtime += tryInt(nr) * (60 if 'h' is str(size)[0] else 1)

        return runtime

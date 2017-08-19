import json
import re
import traceback

from couchpotato import Env
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt, tryFloat, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.base import MovieProvider


log = CPLog(__name__)

autoload = 'OMDBAPI'


class OMDBAPI(MovieProvider):

    urls = {
        'search': 'https://www.omdbapi.com/?apikey=%s&type=movie&%s',
        'info': 'https://www.omdbapi.com/?apikey=%s&type=movie&i=%s',
    }

    http_time_between_calls = 0

    def __init__(self):
        addEvent('info.search', self.search)
        addEvent('movie.search', self.search)
        addEvent('movie.info', self.getInfo)

    def search(self, q, limit = 12):
        if self.isDisabled():
            return []

        name_year = fireEvent('scanner.name_year', q, single = True)

        if not name_year or (name_year and not name_year.get('name')):
            name_year = {
                'name': q
            }

        cache_key = 'omdbapi.cache.%s' % q
        url = self.urls['search'] % (self.getApiKey(), tryUrlencode({'t': name_year.get('name'), 'y': name_year.get('year', '')}))
        cached = self.getCache(cache_key, url, timeout = 3, headers = {'User-Agent': Env.getIdentifier()})

        if cached:
            result = self.parseMovie(cached)
            if result.get('titles') and len(result.get('titles')) > 0:
                log.info('Found: %s', result['titles'][0] + ' (' + str(result.get('year')) + ')')
                return [result]

            return []

        return []

    def getInfo(self, identifier = None, **kwargs):
        if self.isDisabled() or not identifier:
            return {}

        cache_key = 'omdbapi.cache.%s' % identifier
        url = self.urls['info'] % (self.getApiKey(), identifier)
        cached = self.getCache(cache_key, url, timeout = 3, headers = {'User-Agent': Env.getIdentifier()})

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

            if movie.get('Type').lower() != 'movie':
                return movie_data

            tmp_movie = movie.copy()
            for key in tmp_movie:
                tmp_movie_elem = tmp_movie.get(key)
                if not isinstance(tmp_movie_elem, (str, unicode)) or tmp_movie_elem.lower() == 'n/a':
                    del movie[key]

            year = tryInt(movie.get('Year', ''))

            movie_data = {
                'type': 'movie',
                'via_imdb': True,
                'titles': [movie.get('Title')] if movie.get('Title') else [],
                'original_title': movie.get('Title'),
                'images': {
                    'poster': [movie.get('Poster', '')] if movie.get('Poster') and len(movie.get('Poster', '')) > 4 else [],
                },
                'rating': {
                    'imdb': (tryFloat(movie.get('imdbRating', 0)), tryInt(movie.get('imdbVotes', '').replace(',', ''))),
                    #'rotten': (tryFloat(movie.get('tomatoRating', 0)), tryInt(movie.get('tomatoReviews', '').replace(',', ''))),
                },
                'imdb': str(movie.get('imdbID', '')),
                'mpaa': str(movie.get('Rated', '')),
                'runtime': self.runtimeToMinutes(movie.get('Runtime', '')),
                'released': movie.get('Released'),
                'year': year if isinstance(year, int) else None,
                'plot': movie.get('Plot'),
                'genres': splitString(movie.get('Genre', '')),
                'directors': splitString(movie.get('Director', '')),
                'writers': splitString(movie.get('Writer', '')),
                'actors': splitString(movie.get('Actors', '')),
            }
            movie_data = dict((k, v) for k, v in movie_data.items() if v)
        except:
            log.error('Failed parsing IMDB API json: %s', traceback.format_exc())

        return movie_data

    def isDisabled(self):
        if self.getApiKey() == '':
            log.error('No API key provided.')
            return True
        return False

    def getApiKey(self):
        apikey = self.conf('api_key')
        return apikey

    def runtimeToMinutes(self, runtime_str):
        runtime = 0

        regex = '(\d*.?\d+).(h|hr|hrs|mins|min)+'
        matches = re.findall(regex, runtime_str)
        for match in matches:
            nr, size = match
            runtime += tryInt(nr) * (60 if 'h' is str(size)[0] else 1)

        return runtime


config = [{
    'name': 'omdbapi',
    'groups': [
        {
            'tab': 'providers',
            'name': 'tmdb',
            'label': 'OMDB API',
            'hidden': True,
            'description': 'Used for all calls to TheMovieDB.',
            'options': [
                {
                    'name': 'api_key',
                    'default': 'bbc0e412',  # Don't be a dick and use this somewhere else
                    'label': 'Api Key',
                },
            ],
        },
    ],
}]

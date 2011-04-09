from __future__ import with_statement
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import Provider
from couchpotato.environment import Env
from libs.themoviedb import tmdb
import copy

log = CPLog(__name__)

class TMDBWrapper(Provider):
    """Api for theMovieDb"""

    type = 'movie'
    apiUrl = 'http://api.themoviedb.org/2.1'
    imageUrl = 'http://hwcdn.themoviedb.org'

    def __init__(self):
        addEvent('provider.movie.search', self.search)
        addEvent('provider.movie.info', self.getInfo)

        # Use base wrapper
        tmdb.Config.api_key = self.conf('api_key')

    def conf(self, attr):
        return Env.setting(attr, 'themoviedb')

    def search(self, q, limit = 12):
        ''' Find movie by name '''

        if self.isDisabled():
            return False

        log.debug('TheMovieDB - Searching for movie: %s' % q)
        raw = tmdb.search(simplifyString(q))

        results = []
        if raw:
            try:
                nr = 0
                for movie in raw:

                    results.append(self.parseMovie(movie))

                    nr += 1
                    if nr == limit:
                        break

                log.info('TheMovieDB - Found: %s' % [result['titles'][0] + ' (' + str(result['year']) + ')' for result in results])
                return results
            except SyntaxError, e:
                log.error('Failed to parse XML response: %s' % e)
                return False

        return results

    def getInfo(self, identifier = None):
        result = {}

        movie = tmdb.imdbLookup(id = identifier)[0]

        if movie:
            result = self.parseMovie(movie)

        return result

    def parseMovie(self, movie):

        year = str(movie.get('released', 'none'))[:4]

        # Poster url
        poster = self.getImage(movie, type = 'poster')
        backdrop = self.getImage(movie, type = 'backdrop')

        # 1900 is the same as None
        if year == '1900' or year.lower() == 'none':
            year = None

        movie_data = {
            'id': int(movie.get('id', 0)),
            'titles': [toUnicode(movie.get('name'))],
            'images': {
                'posters': [poster],
                'backdrops': [backdrop],
            },
            'imdb': movie.get('imdb_id'),
            'year': year,
            'plot': movie.get('overview', ''),
            'tagline': '',
        }

        # Add alternative names
        for alt in ['original_name', 'alternative_name']:
            alt_name = toUnicode(movie.get(alt))
            if alt_name and not alt_name in movie_data['titles'] and alt_name.lower() != 'none' and alt_name != None:
                movie_data['titles'].append(alt_name)

        return movie_data

    def getImage(self, movie, type = 'poster'):

        image = ''
        for image in movie.get('images', []):
            if(image.get('type') == type):
                image = image.get('thumb')
                break

        return image

    def isDisabled(self):
        if self.conf('api_key') == '':
            log.error('No API key provided.')
            True
        else:
            False

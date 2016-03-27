import random
import traceback
from base64 import b64decode as bd

from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode, ss, tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'TheMovieDb'


class TheMovieDb(MovieProvider):

    http_time_between_calls = .35

    configuration = {
        'images': {
            'secure_base_url': 'https://image.tmdb.org/t/p/',
        },
    }

    ak = ['ZjdmNTE3NzU4NzdlMGJiNjcwMzUyMDk1MmIzYzc4NDA=', 'ZTIyNGZlNGYzZmVjNWY3YjU1NzA2NDFmN2NkM2RmM2E=',
          'YTNkYzExMWU2NjEwNWY2Mzg3ZTk5MzkzODEzYWU0ZDU=', 'ZjZiZDY4N2ZmYTYzY2QyODJiNmZmMmM2ODc3ZjI2Njk=']

    def __init__(self):
        addEvent('info.search', self.search, priority = 3)
        addEvent('movie.search', self.search, priority = 3)
        addEvent('movie.info', self.getInfo, priority = 3)
        addEvent('movie.info_by_tmdb', self.getInfo)
        addEvent('app.load', self.config)

    def config(self):

        # Reset invalid key
        if self.conf('api_key') == '9b939aee0aaafc12a65bf448e4af9543':
            self.conf('api_key', '')

        configuration = self.request('configuration')
        if configuration:
            self.configuration = configuration

    def search(self, q, limit = 3):
        """ Find movie by name """

        if self.isDisabled():
            return False

        log.debug('Searching for movie: %s', q)

        raw = None
        try:
            name_year = fireEvent('scanner.name_year', q, single = True)
            raw = self.request('search/movie', {
                'query': name_year.get('name', q),
                'year': name_year.get('year'),
                'search_type': 'ngram' if limit > 1 else 'phrase'
            }, return_key = 'results')
        except:
            log.error('Failed searching TMDB for "%s": %s', (q, traceback.format_exc()))

        results = []
        if raw:
            try:
                nr = 0

                for movie in raw:
                    parsed_movie = self.parseMovie(movie, extended = False)
                    if parsed_movie:
                        results.append(parsed_movie)

                    nr += 1
                    if nr == limit:
                        break

                log.info('Found: %s', [result['titles'][0] + ' (' + str(result.get('year', 0)) + ')' for result in results])

                return results
            except SyntaxError as e:
                log.error('Failed to parse XML response: %s', e)
                return False

        return results

    def getInfo(self, identifier = None, extended = True, **kwargs):

        if not identifier:
            return {}

        result = self.parseMovie({
            'id': identifier
        }, extended = extended)

        return result or {}

    def parseMovie(self, movie, extended = True):

        # Do request, append other items
        movie = self.request('movie/%s' % movie.get('id'), {
            'append_to_response': 'alternative_titles' + (',images,casts' if extended else '')
        })
        if not movie:
            return

        # Images
        poster = self.getImage(movie, type = 'poster', size = 'w154')
        poster_original = self.getImage(movie, type = 'poster', size = 'original')
        backdrop_original = self.getImage(movie, type = 'backdrop', size = 'original')
        extra_thumbs = self.getMultImages(movie, type = 'backdrops', size = 'original') if extended else []

        images = {
            'poster': [poster] if poster else [],
            #'backdrop': [backdrop] if backdrop else [],
            'poster_original': [poster_original] if poster_original else [],
            'backdrop_original': [backdrop_original] if backdrop_original else [],
            'actors': {},
            'extra_thumbs': extra_thumbs
        }

        # Genres
        try:
            genres = [genre.get('name') for genre in movie.get('genres', [])]
        except:
            genres = []

        # 1900 is the same as None
        year = str(movie.get('release_date') or '')[:4]
        if not movie.get('release_date') or year == '1900' or year.lower() == 'none':
            year = None

        # Gather actors data
        actors = {}
        if extended:

            # Full data
            cast = movie.get('casts', {}).get('cast', [])

            for cast_item in cast:
                try:
                    actors[toUnicode(cast_item.get('name'))] = toUnicode(cast_item.get('character'))
                    images['actors'][toUnicode(cast_item.get('name'))] = self.getImage(cast_item, type = 'profile', size = 'original')
                except:
                    log.debug('Error getting cast info for %s: %s', (cast_item, traceback.format_exc()))

        movie_data = {
            'type': 'movie',
            'via_tmdb': True,
            'tmdb_id': movie.get('id'),
            'titles': [toUnicode(movie.get('title'))],
            'original_title': movie.get('original_title'),
            'images': images,
            'imdb': movie.get('imdb_id'),
            'runtime': movie.get('runtime'),
            'released': str(movie.get('release_date')),
            'year': tryInt(year, None),
            'plot': movie.get('overview'),
            'genres': genres,
            'collection': getattr(movie.get('belongs_to_collection'), 'name', None),
            'actor_roles': actors
        }

        movie_data = dict((k, v) for k, v in movie_data.items() if v)

        # Add alternative names
        if movie_data['original_title'] and movie_data['original_title'] not in movie_data['titles']:
            movie_data['titles'].append(movie_data['original_title'])

        # Add alternative titles
        alternate_titles = movie.get('alternative_titles', {}).get('titles', [])

        for alt in alternate_titles:
            alt_name = alt.get('title')
            if alt_name and alt_name not in movie_data['titles'] and alt_name.lower() != 'none' and alt_name is not None:
                movie_data['titles'].append(alt_name)

        return movie_data

    def getImage(self, movie, type = 'poster', size = 'poster'):

        image_url = ''
        try:
            path = movie.get('%s_path' % type)
            if path:
                image_url = '%s%s%s' % (self.configuration['images']['secure_base_url'], size, path)
        except:
            log.debug('Failed getting %s.%s for "%s"', (type, size, ss(str(movie))))

        return image_url

    def getMultImages(self, movie, type = 'backdrops', size = 'original'):

        image_urls = []
        try:
            for image in movie.get('images', {}).get(type, [])[1:5]:
                image_urls.append(self.getImage(image, 'file', size))
        except:
            log.debug('Failed getting %s.%s for "%s"', (type, size, ss(str(movie))))

        return image_urls

    def request(self, call = '', params = {}, return_key = None):

        params = dict((k, v) for k, v in params.items() if v)
        params = tryUrlencode(params)

        try:
            url = 'https://api.themoviedb.org/3/%s?api_key=%s%s' % (call, self.getApiKey(), '&%s' % params if params else '')
            data = self.getJsonData(url, show_error = False)
        except:
            log.debug('Movie not found: %s, %s', (call, params))
            data = None

        if data and return_key and return_key in data:
            data = data.get(return_key)

        return data

    def isDisabled(self):
        if self.getApiKey() == '':
            log.error('No API key provided.')
            return True
        return False

    def getApiKey(self):
        key = self.conf('api_key')
        return bd(random.choice(self.ak)) if key == '' else key


config = [{
    'name': 'themoviedb',
    'groups': [
        {
            'tab': 'providers',
            'name': 'tmdb',
            'label': 'TheMovieDB',
            'hidden': True,
            'description': 'Used for all calls to TheMovieDB.',
            'options': [
                {
                    'name': 'api_key',
                    'default': '',
                    'label': 'Api Key',
                },
            ],
        },
    ],
}]

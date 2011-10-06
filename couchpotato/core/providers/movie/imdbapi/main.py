from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.movie.base import MovieProvider

log = CPLog(__name__)


class IMDBAPI(MovieProvider):

    urls = {
        'search': 'http://www.imdbapi.com/?t=%s',
        'info': 'http://www.imdbapi.com/?i=%s&tomatoes=true',
    }

    def __init__(self):
        pass
        #addEvent('movie.search', self.search)
        #addEvent('movie.info', self.getInfo)

    def search(self, q, limit = 12):

        search_string = simplifyString(q)
        cache_key = 'imdbapi.cache.%s.%s' % (search_string, limit)
        results = self.getCache(cache_key)

        if not results:
            log.debug('Searching for movie: %s' % q)
            raw = self.urlopen()

            results = []
            if raw:
                try:
                    nr = 0
                    for movie in raw:

                        results.append(self.parseMovie(movie))

                        nr += 1
                        if nr == limit:
                            break

                    log.info('Found: %s' % [result['titles'][0] + ' (' + str(result['year']) + ')' for result in results])

                    self.setCache(cache_key, results)
                    return results
                except SyntaxError, e:
                    log.error('Failed to parse XML response: %s' % e)
                    return False

        return results

    def getInfo(self, identifier = None):

        cache_key = 'tmdb.cache.%s' % identifier
        result = None #self.getCache(cache_key)

        if not result:
            result = {}
            movie = None

            raw = self.urlopen()

            if movie:
                result = self.parseMovie(movie[0])
                self.setCache(cache_key, result)

        return result

    def parseMovie(self, movie):

        # Images
        poster = self.getImage(movie, type = 'poster')
        backdrop = self.getImage(movie, type = 'backdrop')
        poster_original = self.getImage(movie, type = 'poster', size = 'mid')
        backdrop_original = self.getImage(movie, type = 'backdrop', size = 'w1280')

        # Genres
        try:
            genres = self.getCategory(movie, 'genre')
        except:
            genres = []

        # 1900 is the same as None
        year = str(movie.get('released', 'none'))[:4]
        if year == '1900' or year.lower() == 'none':
            year = None

        movie_data = {
            'id': int(movie.get('id', 0)),
            'titles': [toUnicode(movie.get('name'))],
            'original_title': movie.get('original_name'),
            'images': {
                'poster': [poster],
                'backdrop': [backdrop],
                'poster_original': [poster_original],
                'backdrop_original': [backdrop_original],
            },
            'imdb': movie.get('imdb_id'),
            'runtime': movie.get('runtime'),
            'released': movie.get('released'),
            'year': year,
            'plot': movie.get('overview', ''),
            'tagline': '',
            'genres': genres,
        }

        # Add alternative names
        for alt in ['original_name', 'alternative_name']:
            alt_name = toUnicode(movie.get(alt))
            if alt_name and not alt_name in movie_data['titles'] and alt_name.lower() != 'none' and alt_name != None:
                movie_data['titles'].append(alt_name)

        return movie_data

from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.movie.base import MovieProvider
from libs.themoviedb import tmdb

log = CPLog(__name__)


class TheMovieDb(MovieProvider):

    def __init__(self):
        addEvent('movie.by_hash', self.byHash)
        addEvent('movie.search', self.search, priority = 2)
        addEvent('movie.info', self.getInfo, priority = 2)
        addEvent('movie.info_by_tmdb', self.getInfoByTMDBId)

        # Use base wrapper
        tmdb.configure(self.conf('api_key'))

    def byHash(self, file):
        ''' Find movie by hash '''

        if self.isDisabled():
            return False

        cache_key = 'tmdb.cache.%s' % simplifyString(file)
        results = self.getCache(cache_key)

        if not results:
            log.debug('Searching for movie by hash: %s', file)
            try:
                raw = tmdb.searchByHashingFile(file)

                results = []
                if raw:
                    try:
                        results = self.parseMovie(raw)
                        log.info('Found: %s', results['titles'][0] + ' (' + str(results['year']) + ')')

                        self.setCache(cache_key, results)
                        return results
                    except SyntaxError, e:
                        log.error('Failed to parse XML response: %s', e)
                        return False
            except:
                log.debug('No movies known by hash for: %s', file)
                pass

        return results

    def search(self, q, limit = 12):
        ''' Find movie by name '''

        if self.isDisabled():
            return False

        search_string = simplifyString(q)
        cache_key = 'tmdb.cache.%s.%s' % (search_string, limit)
        results = self.getCache(cache_key)

        if not results:
            log.debug('Searching for movie: %s', q)
            raw = tmdb.search(search_string)

            results = []
            if raw:
                try:
                    nr = 0

                    for movie in raw:
                        results.append(self.parseMovie(movie))

                        nr += 1
                        if nr == limit:
                            break

                    log.info('Found: %s', [result['titles'][0] + ' (' + str(result['year']) + ')' for result in results])

                    self.setCache(cache_key, results)
                    return results
                except SyntaxError, e:
                    log.error('Failed to parse XML response: %s', e)
                    return False

        return results

    def getInfo(self, identifier = None):

        if not identifier:
            return {}

        cache_key = 'tmdb.cache.%s' % identifier
        result = self.getCache(cache_key)

        if not result:
            result = {}
            movie = None

            try:
                log.debug('Getting info: %s', cache_key)
                movie = tmdb.imdbLookup(id = identifier)
            except:
                pass

            if movie:
                result = self.parseMovie(movie[0])
                self.setCache(cache_key, result)

        return result

    def getInfoByTMDBId(self, id = None):

        cache_key = 'tmdb.cache.%s' % id
        result = self.getCache(cache_key)

        if not result:
            result = {}
            movie = None

            try:
                log.debug('Getting info: %s', cache_key)
                movie = tmdb.getMovieInfo(id = id)
            except:
                pass

            if movie:
                result = self.parseMovie(movie)
                self.setCache(cache_key, result)

        return result

    def parseMovie(self, movie):

        # Images
        poster = self.getImage(movie, type = 'poster', size = 'cover')
        #backdrop = self.getImage(movie, type = 'backdrop', size = 'w1280')
        poster_original = self.getImage(movie, type = 'poster', size = 'original')
        backdrop_original = self.getImage(movie, type = 'backdrop', size = 'original')

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
            'via_tmdb': True,
            'tmdb_id': int(movie.get('id', 0)),
            'titles': [toUnicode(movie.get('name'))],
            'original_title': movie.get('original_name'),
            'images': {
                'poster': [poster] if poster else [],
                #'backdrop': [backdrop] if backdrop else [],
                'poster_original': [poster_original] if poster_original else [],
                'backdrop_original': [backdrop_original] if backdrop_original else [],
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

    def getImage(self, movie, type = 'poster', size = 'cover'):

        image_url = ''
        for image in movie.get('images', []):
            if(image.get('type') == type) and image.get(size):
                image_url = image.get(size)
                break

        return image_url

    def getCategory(self, movie, type = 'genre'):

        cats = movie.get('categories', {}).get(type)

        categories = []
        for category in cats:
            try:
                categories.append(category)
            except:
                pass

        return categories

    def isDisabled(self):
        if self.conf('api_key') == '':
            log.error('No API key provided.')
            True
        else:
            False

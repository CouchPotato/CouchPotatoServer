from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.info.base import MovieProvider
import tmdb3
import traceback

log = CPLog(__name__)


class TheMovieDb(MovieProvider):

    def __init__(self):
        addEvent('info.search', self.search, priority = 2)
        addEvent('movie.search', self.search, priority = 2)
        addEvent('movie.info', self.getInfo, priority = 2)
        addEvent('movie.info_by_tmdb', self.getInfo)

        # Configure TMDB settings
        tmdb3.set_key(self.conf('api_key'))
        tmdb3.set_cache('null')

    def search(self, q, limit = 12):
        """ Find movie by name """

        if self.isDisabled():
            return False

        search_string = simplifyString(q)
        cache_key = 'tmdb.cache.%s.%s' % (search_string, limit)
        results = self.getCache(cache_key)

        if not results:
            log.debug('Searching for movie: %s', q)

            raw = None
            try:
                raw = tmdb3.searchMovie(search_string)
            except:
                log.error('Failed searching TMDB for "%s": %s', (search_string, traceback.format_exc()))

            results = []
            if raw:
                try:
                    nr = 0

                    for movie in raw:
                        results.append(self.parseMovie(movie, with_titles = False))

                        nr += 1
                        if nr == limit:
                            break

                    log.info('Found: %s', [result['titles'][0] + ' (' + str(result.get('year', 0)) + ')' for result in results])

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
            try:
                log.debug('Getting info: %s', cache_key)
                movie = tmdb3.Movie(identifier)
                result = self.parseMovie(movie)
                self.setCache(cache_key, result)
            except:
                pass

        return result

    def parseMovie(self, movie, with_titles = True):

        cache_key = 'tmdb.cache.%s' % movie.id
        movie_data = self.getCache(cache_key)

        if not movie_data:

            # Images
            poster = self.getImage(movie, type = 'poster', size = 'poster')
            poster_original = self.getImage(movie, type = 'poster', size = 'original')
            backdrop_original = self.getImage(movie, type = 'backdrop', size = 'original')

            images = {
                'poster': [poster] if poster else [],
                #'backdrop': [backdrop] if backdrop else [],
                'poster_original': [poster_original] if poster_original else [],
                'backdrop_original': [backdrop_original] if backdrop_original else [],
            }

            # Genres
            try:
                genres = [genre.name for genre in movie.genres]
            except:
                genres = []

            # 1900 is the same as None
            year = str(movie.releasedate or '')[:4]
            if not movie.releasedate or year == '1900' or year.lower() == 'none':
                year = None

            # Gather actors data
            actors = {}
            for cast_item in movie.cast:
                try:
                    actors[toUnicode(cast_item.name)] = toUnicode(cast_item.character)
                    images['actor %s' % toUnicode(cast_item.name)] = self.getImage(cast_item, type = 'profile', size = 'original')
                except:
                    log.debug('Error getting cast info for %s: %s', (cast_item, traceback.format_exc()))

            movie_data = {
                'type': 'movie',
                'via_tmdb': True,
                'tmdb_id': movie.id,
                'titles': [toUnicode(movie.title)],
                'original_title': movie.originaltitle,
                'images': images,
                'imdb': movie.imdb,
                'runtime': movie.runtime,
                'released': str(movie.releasedate),
                'year': year,
                'plot': movie.overview,
                'genres': genres,
                'collection': getattr(movie.collection, 'name', None),
                'actor_roles': actors
            }

            movie_data = dict((k, v) for k, v in movie_data.iteritems() if v)

            # Add alternative names
            if with_titles:
                movie_data['titles'].append(movie.originaltitle)
                for alt in movie.alternate_titles:
                    alt_name = alt.title
                    if alt_name and alt_name not in movie_data['titles'] and alt_name.lower() != 'none' and alt_name is not None:
                        movie_data['titles'].append(alt_name)

            # Cache movie parsed
            self.setCache(cache_key, movie_data)

        return movie_data

    def getImage(self, movie, type = 'poster', size = 'poster'):

        image_url = ''
        try:
            image_url = getattr(movie, type).geturl(size = 'original')
        except:
            log.debug('Failed getting %s.%s for "%s"', (type, size, movie))

        return image_url

    def isDisabled(self):
        if self.conf('api_key') == '':
            log.error('No API key provided.')
            return True
        return False

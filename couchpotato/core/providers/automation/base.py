from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from couchpotato.core.helpers.encoding import simplifyString
import time

log = CPLog(__name__)


class Automation(Plugin):

    enabled_option = 'automation_enabled'

    interval = 86400
    last_checked = 0

    def __init__(self):
        addEvent('automation.get_movies', self._getMovies)

    def _getMovies(self):

        if not self.canCheck():
            log.debug('Just checked, skipping %s', self.getName())
            return []

        self.last_checked = time.time()

        return self.getIMDBids()

    def search(self, name, year = None):
        result = fireEvent('movie.search', q = '%s %s' % (name, year if year else ''), limit = 1, merge = True)

        if len(result) > 0:
            return result[0].get('imdb')
        else:
            return None

    def isMinimal(self, identifier):
        movie = fireEvent('movie.info', identifier = identifier, merge = True)
        return self.isMinimalMovie(movie)

    def isMinimalMovie(self, movie):
        if movie['rating']:
            rating = movie['rating']['imdb'][0]
            movie['votes'] =  movie['rating']['imdb'][1]
            movie['rating'] = movie['rating']['imdb'][0]
        identifier = movie['imdb']
        for minimal_type in ['year', 'rating', 'votes']:
            type_value = movie.get(minimal_type, 0)
            type_min = self.getMinimal(minimal_type)
            if type_value < type_min:
                log.info('%s too low for %s, need %s has %s', (minimal_type, identifier, type_min, type_value))
                return False

        return True

    def getIMDBFromTitle(self, title):
        cache_key = u'%s/%s' % (__name__, simplifyString(title))
        movies = Env.get('cache').get(cache_key)

        if not movies:
            movies = fireEvent('movie.searchimdb', q = title, merge = True)
            Env.get('cache').set(cache_key, movies)
        
        try:
            return movies[0]
        
        except:
            log.info("No results for " + title)

    def getMinimal(self, min_type):
        return Env.setting(min_type, 'automation')

    def getIMDBids(self):
        return []

    def canCheck(self):
        return time.time() > self.last_checked + self.interval

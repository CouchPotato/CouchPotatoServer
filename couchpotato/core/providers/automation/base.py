from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
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

    def search(self, name, year = None, imdb_only = False):

        prop_name = 'automation.cached.%s.%s' % (name, year)
        cached_imdb = Env.prop(prop_name, default = False)
        if cached_imdb and imdb_only:
            return cached_imdb

        result = fireEvent('movie.search', q = '%s %s' % (name, year if year else ''), limit = 1, merge = True)

        if len(result) > 0:
            if imdb_only and result[0].get('imdb'):
                Env.prop(prop_name, result[0].get('imdb'))

            return result[0].get('imdb') if imdb_only else result[0]
        else:
            return None

    def isMinimalMovie(self, movie):
        if not movie.get('rating'):
            return False

        if movie['rating'] and movie['rating'].get('imdb'):
            movie['votes'] = movie['rating']['imdb'][1]
            movie['rating'] = movie['rating']['imdb'][0]

        for minimal_type in ['year', 'rating', 'votes']:
            type_value = movie.get(minimal_type, 0)
            type_min = self.getMinimal(minimal_type)
            if type_value < type_min:
                log.info('%s too low for %s, need %s has %s', (minimal_type, movie['imdb'], type_min, type_value))
                return False

        return True

    def getMinimal(self, min_type):
        return Env.setting(min_type, 'automation')

    def getIMDBids(self):
        return []

    def canCheck(self):
        return time.time() > self.last_checked + self.interval

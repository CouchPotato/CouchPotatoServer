from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import Provider
from couchpotato.environment import Env
from couchpotato.core.helpers.variable import splitString
import time

log = CPLog(__name__)


class Automation(Provider):

    enabled_option = 'automation_enabled'
    chart_enabled_option = 'chart_display_enabled'
    http_time_between_calls = 2

    interval = 1800
    last_checked = 0

    def __init__(self):
        addEvent('automation.get_movies', self._getMovies)
        addEvent('automation.get_chart_list', self._getChartList)

    def _getMovies(self):

        if self.isDisabled():
            return

        if not self.canCheck():
            log.debug('Just checked, skipping %s', self.getName())
            return []

        self.last_checked = time.time()

        return self.getIMDBids()

    def _getChartList(self):

        if not (self.conf(self.chart_enabled_option) or self.conf(self.chart_enabled_option) is None):
            return

        return self.getChartList()

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
            log.info('ignoring %s as no rating is available for.', (movie['original_title']))
            return False

        if movie['rating'] and movie['rating'].get('imdb'):
            movie['votes'] = movie['rating']['imdb'][1]
            movie['rating'] = movie['rating']['imdb'][0]

        for minimal_type in ['year', 'rating', 'votes']:
            type_value = movie.get(minimal_type, 0)
            type_min = self.getMinimal(minimal_type)
            if type_value < type_min:
                log.info('%s too low for %s, need %s has %s', (minimal_type, movie['original_title'], type_min, type_value))
                return False

        movie_genres = [genre.lower() for genre in movie['genres']]
        required_genres = splitString(self.getMinimal('required_genres').lower())
        ignored_genres = splitString(self.getMinimal('ignored_genres').lower())

        req_match = 0
        for req_set in required_genres:
            req = splitString(req_set, '&')
            req_match += len(list(set(movie_genres) & set(req))) == len(req)

        if self.getMinimal('required_genres') and req_match == 0:
            log.info2('Required genre(s) missing for %s', movie['original_title'])
            return False

        for ign_set in ignored_genres:
            ign = splitString(ign_set, '&')
            if len(list(set(movie_genres) & set(ign))) == len(ign):
                log.info2('%s has blacklisted genre(s): %s', (movie['original_title'], ign))
                return False

        return True

    def getMinimal(self, min_type):
        return Env.setting(min_type, 'automation')

    def getIMDBids(self):
        return []

    def getChartList(self):
        # Example return: [ {'name': 'Display name of list', 'list': []} ]
        return

    def canCheck(self):
        return time.time() > self.last_checked + self.interval

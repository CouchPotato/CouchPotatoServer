from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env

log = CPLog(__name__)


class Automation(Plugin):

    def __init__(self):

        fireEvent('schedule.interval', 'automation.add_movies', self.addMovies, hours = self.conf('hour', default = 12))

        if not Env.get('dev'):
            addEvent('app.load', self.addMovies)

    def addMovies(self):

        movies = fireEvent('automation.get_movies', merge = True)
        movie_ids = []

        for imdb_id in movies:
            prop_name = 'automation.added.%s' % imdb_id
            added = Env.prop(prop_name, default = False)
            if not added:
                added_movie = fireEvent('movie.add', params = {'identifier': imdb_id}, force_readd = False, search_after = False, single = True)
                movie_ids.append(added_movie['id'])
                Env.prop(prop_name, True)

        for movie_id in movie_ids:
            movie_dict = fireEvent('movie.get', movie_id, single = True)
            fireEvent('searcher.single', movie_dict)

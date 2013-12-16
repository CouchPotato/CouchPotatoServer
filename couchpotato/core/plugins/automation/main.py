from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env

log = CPLog(__name__)


class Automation(Plugin):

    def __init__(self):

        addEvent('app.load', self.setCrons)

        if not Env.get('dev'):
            addEvent('app.load', self.addMovies)

        addEvent('setting.save.automation.hour.after', self.setCrons)

    def setCrons(self):
        fireEvent('schedule.interval', 'automation.add_movies', self.addMovies, hours = self.conf('hour', default = 12))

    def addMovies(self):

        movies = fireEvent('automation.get_movies', merge = True)
        movie_ids = []

        for imdb_id in movies:

            if self.shuttingDown():
                break

            prop_name = 'automation.added.%s' % imdb_id
            added = Env.prop(prop_name, default = False)
            if not added:
                added_movie = fireEvent('movie.add', params = {'identifier': imdb_id}, force_readd = False, search_after = False, update_library = True, single = True)
                if added_movie:
                    movie_ids.append(added_movie['id'])
                Env.prop(prop_name, True)

        for movie_id in movie_ids:

            if self.shuttingDown():
                break

            movie_dict = fireEvent('media.get', movie_id, single = True)
            fireEvent('movie.searcher.single', movie_dict)

        return True

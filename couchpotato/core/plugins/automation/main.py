from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env

log = CPLog(__name__)


class Automation(Plugin):

    def __init__(self):

        fireEvent('schedule.interval', 'updater.check', self.addMovies, hours = self.conf('hour', default = 12))

        if not Env.get('dev'):
            addEvent('app.load', self.addMovies)

    def addMovies(self):

        movies = fireEvent('automation.get_movies', merge = True)
        for imdb_id in movies:
            fireEvent('movie.add', params = {'identifier': imdb_id}, force_readd = False)

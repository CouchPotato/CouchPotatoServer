from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation

log = CPLog(__name__)


class Moviemeter(Automation, RSS):

    interval = 1800
    rss_url = 'http://www.moviemeter.nl/rss/cinema'

    def getIMDBids(self):

        movies = []

        rss_movies = self.getRSSData(self.rss_url)

        for movie in rss_movies:

            name_year = fireEvent('scanner.name_year', self.getTextElement(movie, 'title'), single = True)
            imdb = self.search(name_year.get('name'), name_year.get('year'))

            if imdb and self.isMinimalMovie(imdb):
                movies.append(imdb['imdb'])

        return movies

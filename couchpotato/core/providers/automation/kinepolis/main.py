from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import datetime

log = CPLog(__name__)


class Kinepolis(Automation, RSS):

    interval = 1800
    rss_url = 'http://kinepolis.be/nl/top10-box-office/feed'

    def getIMDBids(self):

        movies = []

        rss_movies = self.getRSSData(self.rss_url)

        for movie in rss_movies:
            name = self.getTextElement(movie, 'title')
            year = datetime.datetime.now().strftime('%Y')

            imdb = self.search(name, year)

            if imdb and self.isMinimalMovie(imdb):
                movies.append(imdb['imdb'])

        return movies

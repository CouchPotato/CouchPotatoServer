from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation

log = CPLog(__name__)


class Bluray(Automation, RSS):

    interval = 1800
    rss_url = 'http://www.blu-ray.com/rss/newreleasesfeed.xml'

    def getIMDBids(self):

        movies = []

        rss_movies = self.getRSSData(self.rss_url)

        for movie in rss_movies:
            name = self.getTextElement(movie, 'title').lower().split('blu-ray')[0].strip('(').rstrip()
            year = self.getTextElement(movie, 'description').split('|')[1].strip('(').strip()

            if not name.find('/') == -1: # make sure it is not a double movie release
                continue

            if tryInt(year) < self.getMinimal('year'):
                continue

            imdb = self.search(name, year)

            if imdb:
                if self.isMinimalMovie(imdb):
                    movies.append(imdb['imdb'])

        return movies

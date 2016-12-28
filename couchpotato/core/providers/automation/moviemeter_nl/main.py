from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import md5
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import datetime
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class Moviemeter(Automation, RSS):

    interval = 1800
    rss_url = 'http://www.moviemeter.nl/rss/cinema'

    def getIMDBids(self):

        if self.isDisabled():
            return

        movies = []

        cache_key = 'moviemeter.%s' % md5(self.rss_url)
        rss_data = self.getCache(cache_key, self.rss_url)
        data = XMLTree.fromstring(rss_data)

        if data is not None:
            rss_movies = self.getElements(data, 'channel/item')

            for movie in rss_movies:
                name = self.getTextElement(movie, "title")
                year = datetime.datetime.now().strftime("%Y")

                imdb = self.search(name, year)

                if imdb and self.isMinimalMovie(imdb):
                    movies.append(imdb['imdb'])

        return movies

from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import md5, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class Bluray(Automation, RSS):

    interval = 1800
    rss_url = 'http://www.blu-ray.com/rss/newreleasesfeed.xml'

    def getIMDBids(self):

        if self.isDisabled():
            return

        movies = []

        cache_key = 'bluray.%s' % md5(self.rss_url)
        rss_data = self.getCache(cache_key, self.rss_url)
        data = XMLTree.fromstring(rss_data)

        if data is not None:
            rss_movies = self.getElements(data, 'channel/item')

            for movie in rss_movies:
                name = self.getTextElement(movie, "title").lower().split("blu-ray")[0].strip("(").rstrip()
                year = self.getTextElement(movie, "description").split("|")[1].strip("(").strip()

                if not name.find("/") == -1: # make sure it is not a double movie release
                    continue

                if tryInt(year) < self.getMinimal('year'):
                    continue

                imdb = self.search(name, year)

                if imdb:
                    if self.isMinimalMovie(imdb):
                        movies.append(imdb['imdb'])

        return movies

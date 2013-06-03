from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
from xml.etree.ElementTree import QName
import datetime
import re

log = CPLog(__name__)

class Rottentomatoes(Automation, RSS):

    interval = 1800
    urls = {
        'namespace': 'http://www.rottentomatoes.com/xmlns/rtmovie/',
        'theater': 'http://www.rottentomatoes.com/syndication/rss/in_theaters.xml',
    }

    def getIMDBids(self):

        movies = []

        rss_movies = self.getRSSData(self.urls['theater'])
        rating_tag = str(QName(self.urls['namespace'], 'tomatometer_percent'))

        for movie in rss_movies:

            value = self.getTextElement(movie, "title")
            result = re.search('(?<=%\s).*', value)

            if result:

                log.info2('Something smells...')
                rating = tryInt(self.getTextElement(movie, rating_tag))
                name = result.group(0)

                if rating < tryInt(self.conf('tomatometer_percent')):
                    log.info2('%s seems to be rotten...', name)
                else:

                    log.info2('Found %s fresh enough movies, enqueuing: %s', (rating, name))
                    year = datetime.datetime.now().strftime("%Y")
                    imdb = self.search(name, year)

                    if imdb:
                        movies.append(imdb['imdb'])

        return movies

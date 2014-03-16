from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
from xml.etree.ElementTree import QName
import datetime
import re

log = CPLog(__name__)


class Rottentomatoes(Automation, RSS):

    interval = 1800

    def getIMDBids(self):

        movies = []

        rotten_tomatoes_namespace = 'http://www.rottentomatoes.com/xmlns/rtmovie/'
        urls = dict(zip(splitString(self.conf('automation_urls')), [tryInt(x) for x in splitString(self.conf('automation_urls_use'))]))

        for url in urls:

            if not urls[url]:
                continue

            rss_movies = self.getRSSData(url)
            rating_tag = str(QName(rotten_tomatoes_namespace, 'tomatometer_percent'))

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

                        if imdb and self.isMinimalMovie(imdb):
                            movies.append(imdb['imdb'])

        return movies

from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import md5
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
from xml.etree.ElementTree import QName
import datetime
import xml.etree.ElementTree as XMLTree
import re

log = CPLog(__name__)

class Rottentomatoes(Automation, RSS):

    interval = 1800
    rss_url = 'http://www.rottentomatoes.com/syndication/rss/in_theaters.xml'

    def getIMDBids(self):

        if self.isDisabled():
            return

        movies = []

        cache_key = 'rottentomatoes.%s' % md5(self.rss_url)
        rss_data = self.getCache(cache_key, self.rss_url)
        data = XMLTree.fromstring(rss_data)

        if data:

            namespace = 'http://www.rottentomatoes.com/xmlns/rtmovie/'
            rating_tag = str(QName(namespace, 'tomatometer_percent'))
            rss_movies = self.getElements(data, 'channel/item')

            for movie in rss_movies:

                value = self.getTextElement(movie, "title")
                result = re.search('(?<=%\s).*', value)

                if result:

                    log.info('Something smells...')
                    rating = int(self.getTextElement(movie, rating_tag))
                    name = result.group(0)

                    if rating < int(self.conf('tomatometer_percent')):

                        log.info('%s seems to be rotten...' % name)

                    else:

                        log.info('You find %s fresh enough though, enqueuing: %s' % (rating, name))
                        year = datetime.datetime.now().strftime("%Y")
                        imdb = self.search(name, year)

                        if imdb:
                            movies.append(imdb['imdb'])

        return movies

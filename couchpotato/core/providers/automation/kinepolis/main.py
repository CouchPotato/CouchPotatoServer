from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import md5
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
from couchpotato.environment import Env
from dateutil.parser import parse
import time
import traceback
import xml.etree.ElementTree as XMLTree
import datetime

log = CPLog(__name__)


class Kinepolis(Automation, RSS):

    interval = 1800
    rss_url = 'http://kinepolis.be/nl/top10-box-office/feed'

    def getIMDBids(self):
        
        if self.isDisabled():
            return
        
        movies = []
        RSSMovie = {'name': 'placeholder', 'year' : 'placeholder'}

        cache_key = 'kinepolis.%s' % md5(self.rss_url)
        rss_data = self.getCache(cache_key, self.rss_url)
        data = XMLTree.fromstring(rss_data)

        if data:
            rss_movies = self.getElements(data, 'channel/item')
            
            for movie in rss_movies:
                RSSMovie['name'] = self.getTextElement(movie, "title")
                currentYear = datetime.datetime.now().strftime("%Y")
                RSSMovie['year'] = currentYear

                log.info('Release found: %s.' % RSSMovie)
                imdb = self.getIMDBFromTitle(RSSMovie['name'] + ' ' + RSSMovie['year'])

                if imdb:
                    movies.append(imdb['imdb'])

        return movies
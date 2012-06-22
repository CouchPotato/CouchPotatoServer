from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import md5
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
from couchpotato.environment import Env
import traceback
import xml.etree.ElementTree as XMLTree
import json

log = CPLog(__name__)


class Bluray(Automation, RSS):

    interval = 1800
    rss_url = 'http://www.blu-ray.com/rss/newreleasesfeed.xml'

    def getIMDBids(self):
        
        if self.isDisabled():
            return
        
        movies = []
        RSSMovie = {'name': 'placeholder', 'year' : 'placeholder'}
        RSSMovies = []

        cache_key = 'bluray.%s' % md5(self.rss_url)
        rss_data = self.getCache(cache_key, self.rss_url)
        data = XMLTree.fromstring(rss_data)

        if data:
            rss_movies = self.getElements(data, 'channel/item')
            
            for movie in rss_movies:
                RSSMovie['name'] = self.getTextElement(movie, "title").lower().split("blu-ray")[0].strip("(").rstrip()
                RSSMovie['year'] = self.getTextElement(movie, "description").split("|")[1].strip("(").strip()
                
                if not RSSMovie['name'].find("/") == -1: # make sure it is not a double movie release
                    continue

                if int(RSSMovie['year']) < Env.setting('year', 'automation'): #do year filtering
                    continue

                for test in RSSMovies:
                    if test.values() == RSSMovie.values(): # make sure we did not already include it...
                        break
                else:
                    log.info('Release found: %s.' % RSSMovie)
                    RSSMovies.append(RSSMovie.copy())

            if not RSSMovies:
                log.info('No movies found.')
                return

            log.info("Applying IMDB filter to found movies...")

            for RSSMovie in RSSMovies:
                imdb = self.getIMDBFromTitle(RSSMovie['name'] + ' ' + RSSMovie['year'])
                
                if imdb:
                    if self.isMinimalMovie(imdb):
                        movies.append(imdb['imdb'])

        return movies
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import md5, getImdb
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import traceback
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class IMDB(Automation, RSS):

    interval = 1800

    def getIMDBids(self):

        if self.isDisabled():
            return

        movies = []

        enablers = self.conf('automation_urls_use').split(',')

        index = -1
        for rss_url in self.conf('automation_urls').split(','):

            index += 1
            if not enablers[index]:
                continue
            elif 'rss.imdb' not in rss_url:
                log.error('This isn\'t the correct url.: %s', rss_url)
                continue

            try:
                cache_key = 'imdb.rss.%s' % md5(rss_url)

                rss_data = self.getCache(cache_key, rss_url)
                data = XMLTree.fromstring(rss_data)
                rss_movies = self.getElements(data, 'channel/item')

                for movie in rss_movies:
                    imdb = getImdb(self.getTextElement(movie, "link"))
                    movies.append(imdb)

            except:
                log.error('Failed loading IMDB watchlist: %s %s', (rss_url, traceback.format_exc()))

        return movies

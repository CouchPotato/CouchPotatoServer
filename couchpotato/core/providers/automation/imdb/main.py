from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import md5, getImdb
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
from couchpotato.environment import Env
from dateutil.parser import parse
import time
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

            prop_name = 'automation.imdb.last_update.%s' % md5(rss_url)
            last_update = float(Env.prop(prop_name, default = 0))

            last_movie_added = 0
            try:
                cache_key = 'imdb.rss.%s' % md5(rss_url)

                rss_data = self.getCache(cache_key, rss_url)
                data = XMLTree.fromstring(rss_data)
                rss_movies = self.getElements(data, 'channel/item')

                for movie in rss_movies:
                    created = int(time.mktime(parse(self.getTextElement(movie, "pubDate")).timetuple()))
                    imdb = getImdb(self.getTextElement(movie, "link"))

                    if created > last_movie_added:
                        last_movie_added = created

                    if not imdb or created <= last_update:
                        continue

                    movies.append(imdb)

            except:
                log.error('Failed loading IMDB watchlist: %s %s', (rss_url, traceback.format_exc()))

            Env.prop(prop_name, last_movie_added)

        return movies

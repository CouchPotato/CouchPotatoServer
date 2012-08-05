from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import md5
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
from couchpotato.environment import Env
from dateutil.parser import parse
from xml.etree.ElementTree import ParseError
import time
import traceback
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class MoviesIO(Automation, RSS):

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

            prop_name = 'automation.moviesio.last_update.%s' % md5(rss_url)
            last_update = float(Env.prop(prop_name, default = 0))

            last_movie_added = 0
            try:
                cache_key = 'imdb.rss.%s' % md5(rss_url)

                rss_data = self.getCache(cache_key, rss_url, headers = {'Referer': ''})
                data = XMLTree.fromstring(rss_data)
                rss_movies = self.getElements(data, 'channel/item')

                for movie in rss_movies:
                    created = int(time.mktime(parse(self.getTextElement(movie, "pubDate")).timetuple()))

                    if created > last_movie_added:
                        last_movie_added = created
                    if created <= last_update:
                        continue

                    nameyear = fireEvent('scanner.name_year', self.getTextElement(movie, "title"), single = True)
                    imdb = self.search(nameyear.get('name'), nameyear.get('year'), imdb_only = True)

                    if not imdb:
                        continue

                    movies.append(imdb)
            except ParseError:
                log.debug('Failed loading Movies.io watchlist, probably empty: %s', (rss_url))
            except:
                log.error('Failed loading Movies.io watchlist: %s %s', (rss_url, traceback.format_exc()))

            Env.prop(prop_name, last_movie_added)

        return movies

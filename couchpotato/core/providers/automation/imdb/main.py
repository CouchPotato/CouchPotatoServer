from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import md5, getImdb, splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import traceback

log = CPLog(__name__)


class IMDB(Automation, RSS):

    interval = 1800

    def getIMDBids(self):

        if self.isDisabled():
            return

        movies = []

        enablers = [tryInt(x) for x in splitString(self.conf('automation_urls_use'))]
        urls = splitString(self.conf('automation_urls'))

        index = -1
        for url in urls:

            index += 1
            if not enablers[index]:
                continue

            try:
                cache_key = 'imdb.rss.%s' % md5(url)
                rss_data = self.getCache(cache_key, url)
                imdbs = getImdb(rss_data, multiple = True)

                for imdb in imdbs:
                    movies.append(imdb)

            except:
                log.error('Failed loading IMDB watchlist: %s %s', (url, traceback.format_exc()))

        return movies

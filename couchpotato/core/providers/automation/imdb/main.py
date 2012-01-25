from couchpotato.core.helpers.variable import md5, getImdb
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import StringIO
import csv
import traceback

log = CPLog(__name__)


class IMDB(Automation):

    interval = 1800

    def getIMDBids(self):

        if self.isDisabled():
            return

        movies = []

        for csv_url in self.conf('automation_urls').split(','):
            try:
                cache_key = 'imdb_csv.%s' % md5(csv_url)
                csv_data = self.getCache(cache_key, csv_url)
                csv_reader = csv.reader(StringIO.StringIO(csv_data))
                csv_reader.next()

                for row in csv_reader:
                    imdb = getImdb(str(row))
                    if imdb:
                        movies.append(imdb)
            except:
                log.error('Failed loading IMDB watchlist: %s %s' % (csv_url, traceback.format_exc()))

        return movies

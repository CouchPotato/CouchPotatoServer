from couchpotato.core.helpers.variable import md5
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
from couchpotato.environment import Env
from dateutil.parser import parse
import StringIO
import csv
import time
import traceback

log = CPLog(__name__)


class IMDB(Automation):

    interval = 1800

    def getIMDBids(self):

        if self.isDisabled():
            return

        movies = []
        headers = {}

        for csv_url in self.conf('automation_urls').split(','):
            prop_name = 'automation.imdb.last_update.%s' % md5(csv_url)
            last_update = float(Env.prop(prop_name, default = 0))

            try:
                cache_key = 'imdb_csv.%s' % md5(csv_url)
                csv_data = self.getCache(cache_key, csv_url)
                csv_reader = csv.reader(StringIO.StringIO(csv_data))
                if not headers:
                    nr = 0
                    for column in csv_reader.next():
                        headers[column] = nr
                        nr += 1

                for row in csv_reader:
                    created = int(time.mktime(parse(row[headers['created']]).timetuple()))
                    if created < last_update:
                        continue

                    imdb = row[headers['const']]
                    if imdb:
                        movies.append(imdb)
            except:
                log.error('Failed loading IMDB watchlist: %s %s' % (csv_url, traceback.format_exc()))

            Env.prop(prop_name, time.time())


        return movies

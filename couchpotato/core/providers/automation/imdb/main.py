import traceback

from bs4 import BeautifulSoup
from couchpotato import fireEvent
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import getImdb, splitString, tryInt

from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation

from couchpotato.core.providers.base import MultiProvider


log = CPLog(__name__)


class IMDB(MultiProvider):

    def getTypes(self):
        return [IMDBWatchlist, IMDBAutomation]


class IMDBBase(Automation, RSS):

    interval = 1800

    def getInfo(self, imdb_id):
        return fireEvent('movie.info', identifier = imdb_id, merge = True)


class IMDBWatchlist(IMDBBase):

    enabled_option = 'automation_enabled'

    def getIMDBids(self):

        movies = []

        watchlist_enablers = [tryInt(x) for x in splitString(self.conf('automation_urls_use'))]
        watchlist_urls = splitString(self.conf('automation_urls'))

        index = -1
        for watchlist_url in watchlist_urls:

            index += 1
            if not watchlist_enablers[index]:
                continue

            try:
                log.debug('Started IMDB watchlists: %s', watchlist_url)
                rss_data = self.getHTMLData(watchlist_url)
                imdbs = getImdb(rss_data, multiple = True) if rss_data else []

                for imdb in imdbs:
                    movies.append(imdb)

                    if self.shuttingDown():
                        break

            except:
                log.error('Failed loading IMDB watchlist: %s %s', (watchlist_url, traceback.format_exc()))

        return movies


class IMDBAutomation(IMDBBase):

    enabled_option = 'automation_providers_enabled'

    chart_urls = {
        'theater': 'http://www.imdb.com/movies-in-theaters/',
        'top250': 'http://www.imdb.com/chart/top',
        'boxoffice': 'http://www.imdb.com/chart/',
    }

    chart_names = {
        'theater': 'IMDB - Movies in Theaters',
        'top250': 'IMDB - Top 250 Movies',
        'boxoffice': 'IMDB - Box Office',
    }

    first_table = ['boxoffice']

    def getIMDBids(self):

        movies = []

        for url in self.chart_urls:
            if self.conf('automation_charts_%s' % url):
                data = self.getHTMLData(self.chart_urls[url])
                if data:
                    html = BeautifulSoup(data)

                    try:
                        result_div = html.find('div', attrs = {'id': 'main'})

                        try:
                            if url in self.first_table:
                                table = result_div.find('table')
                                result_div = table if table else result_div
                        except:
                            pass

                        imdb_ids = getImdb(str(result_div), multiple = True)

                        for imdb_id in imdb_ids:
                            info = self.getInfo(imdb_id)
                            if info and self.isMinimalMovie(info):
                                movies.append(imdb_id)

                            if self.shuttingDown():
                                break

                    except:
                        log.error('Failed loading IMDB chart results from %s: %s', (url, traceback.format_exc()))

        return movies


    def getChartList(self):
        # Nearly identical to 'getIMDBids', but we don't care about minimalMovie and return all movie data (not just id)
        movie_lists = []
        max_items = int(self.conf('max_items', section='charts', default=5))

        for url in self.chart_urls:
            if self.conf('chart_display_%s' % url):
                movie_list = {'name': self.chart_names[url], 'list': []}
                data = self.getHTMLData(self.chart_urls[url])
                if data:
                    html = BeautifulSoup(data)

                    try:
                        result_div = html.find('div', attrs = {'id': 'main'})

                        try:
                            if url in self.first_table:
                                table = result_div.find('table')
                                result_div = table if table else result_div
                        except:
                            pass

                        imdb_ids = getImdb(str(result_div), multiple = True)

                        for imdb_id in imdb_ids[0:max_items]:
                            info = self.getInfo(imdb_id)
                            movie_list['list'].append(info)

                            if self.shuttingDown():
                                break
                    except:
                        log.error('Failed loading IMDB chart results from %s: %s', (url, traceback.format_exc()))

                    if movie_list['list']:
                            movie_lists.append(movie_list)


        return movie_lists

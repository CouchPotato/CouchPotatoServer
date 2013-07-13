from bs4 import BeautifulSoup
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import getImdb, splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import re
import traceback

log = CPLog(__name__)


class IMDB(Automation, RSS):

    interval = 1800

    chart_urls = {
        'theater': 'http://www.imdb.com/movies-in-theaters/',
        'top250': 'http://www.imdb.com/chart/top',
    }


    def getIMDBids(self):

        movies = []

        # Handle Chart URLs
        if self.conf('automation_charts_theaters_use'):
            log.debug('Started IMDB chart: %s', self.chart_urls['theater'])
            data = self.getHTMLData(self.chart_urls['theater'])				   
            if data:
                html = BeautifulSoup(data)

                try:		        
                    result_div = html.find('div', attrs = {'id': 'main'})	        

                    entries = result_div.find_all('div', attrs = {'itemtype': 'http://schema.org/Movie'})

                    for entry in entries:
                        title = entry.find('h4', attrs = {'itemprop': 'name'}).getText()

                        log.debug('Identified title: %s', title)
                        result = re.search('(.*) \((.*)\)', title)

                        if result:
                            name = result.group(1)
                            year = result.group(2)

                            imdb = self.search(name, year)

                            if imdb and self.isMinimalMovie(imdb):
                                movies.append(imdb['imdb'])				        				

                except:
                    log.error('Failed loading IMDB chart results from %s: %s', (self.chart_urls['theater'], traceback.format_exc()))

        if self.conf('automation_charts_top250_use'):
            log.debug('Started IMDB chart: %s', self.chart_urls['top250'])
            data = self.getHTMLData(self.chart_urls['top250'])				   
            if data:
                html = BeautifulSoup(data)

                try:		        
                    result_div = html.find('div', attrs = {'id': 'main'})	        

                    result_table = result_div.find_all('table')[1]
                    entries = result_table.find_all('tr') 

                    for entry in entries[1:]:
                        title = entry.find_all('td')[2].getText() 												

                        log.debug('Identified title: %s', title)
                        result = re.search('(.*) \((.*)\)', title)

                        if result:
                            name = result.group(1)
                            year = result.group(2)

                            imdb = self.search(name, year)

                            if imdb and self.isMinimalMovie(imdb):
                                movies.append(imdb['imdb'])				        				

                except:
                    log.error('Failed loading IMDB chart results from %s: %s', (self.chart_urls['theater'], traceback.format_exc()))


        # Handle Watchlists
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

            except:
                log.error('Failed loading IMDB watchlist: %s %s', (url, traceback.format_exc()))


        # Return the combined resultset
        return movies

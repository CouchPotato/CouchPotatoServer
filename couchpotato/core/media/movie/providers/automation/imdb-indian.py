import traceback
from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt, splitString, removeEmpty
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation
from couchpotato import fireEvent


log = CPLog(__name__)

autoload = 'IMDBIndian'


class IMDBIndian(Automation):

    url = 'https://www.imdb.com/india/released/'

    charts = {
        'imdbindiantrending': {
            'order': 1,
            'name': 'Trending Indian Movies',
            'url': 'https://www.imdb.com/india/released/',
        }
    }

    interval = 1800

    def getIMDBids(self):

        soup = BeautifulSoup(self.getHTMLData(self.url))

        items = soup.find_all('div', attrs={'class': 'trending-list-rank-item'})

        movies = []

        for item in items:
            containers = item.find_all('div', attrs={'class': 'trending-list-rank-item-data-container'})
            for container in containers:
                span = container.find('span', attrs={'class': 'trending-list-rank-item-name'})
                a = span.find('a')
                title_link = a.attrs['href']
                imdb_id = title_link.split('/')[2]
                
                info = fireEvent('movie.info', identifier = imdb_id, extended = False, merge = True)
                if self.isMinimalMovie(info):
                    movies.append(imdb_id)
        
        return movies
    
    def getChartList(self):
        # Nearly identical to 'getIMDBids', but we don't care about minimalMovie and return all movie data (not just id)
        max_items = 10

        cache_key = 'imdbindian.charts'

        movie_list = {
            'name': 'IMDB - Trending Indian Movies',
            'url': self.url,
            'order': 1,
            'list': self.getCache(cache_key) or []
        }

        if not movie_list['list']:
            try:
                soup = BeautifulSoup(self.getHTMLData(self.url))
                items = soup.find_all('div', attrs={'class': 'trending-list-rank-item'})

                imdb_ids = []

                for item in items:
                    containers = item.find_all('div', attrs={'class': 'trending-list-rank-item-data-container'})
                    for container in containers:
                        span = container.find('span', attrs={'class': 'trending-list-rank-item-name'})
                        a = span.find('a')
                        title_link = a.attrs['href']
                        imdb_id = title_link.split('/')[2]
                        imdb_ids.append(imdb_id)
                

                # log.info('Fetched ' + str(len(imdb_ids)) + ' imdb_ids')

                for imdb_id in imdb_ids[0:max_items]:
                    is_movie = fireEvent('movie.is_movie', identifier = imdb_id, adding = False, single = True)
                    if not is_movie:
                        log.debug('Not a movie ' + imdb_id)
                        continue

                    info = fireEvent('movie.info', identifier = imdb_id, extended = False, adding = False, merge = True)
                    movie_list['list'].append(info)

                    if self.shuttingDown():
                        break
            except:
                log.error('Failed loading IMDB chart results: %s', traceback.format_exc())

            self.setCache(cache_key, movie_list['list'], timeout = 259200)

        return [movie_list]

config = [{
    'name': 'imdbindian',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'imdb_indian_automation',
            'label': 'IMDB Indian',
            'description': 'Import from <a href="https://www.imdb.com/india/released/" target="_blank">Trending Indian Movies</a>',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                }
            ],
        },
        {
            'tab': 'display',
            'list': 'charts_providers',
            'name': 'imdbindian_charts_display',
            'label': 'IMDB Trending Indian Movies',
            'description': 'Display <a href="https://www.imdb.com/india/released/" target="_blank">Trending Indian Movies</a> from IMDB',
            'options': [
                {
                    'name': 'chart_display_enabled',
                    'default': False,
                    'type': 'enabler',
                },
            ],
        },
    ],
}]

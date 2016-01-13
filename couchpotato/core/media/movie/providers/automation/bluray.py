import traceback

from bs4 import BeautifulSoup
from couchpotato import fireEvent
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation


log = CPLog(__name__)

autoload = 'Bluray'


class Bluray(Automation, RSS):

    interval = 1800
    rss_url = 'http://www.blu-ray.com/rss/newreleasesfeed.xml'
    backlog_url = 'http://www.blu-ray.com/movies/movies.php?show=newreleases&page=%s'
    display_url = 'http://www.blu-ray.com/movies/movies.php?show=newreleases'
    chart_order = 1

    def getIMDBids(self):

        movies = []

        if self.conf('backlog'):

            cookie = {'Cookie': 'listlayout_7=full'}
            page = 0
            while True:
                page += 1

                url = self.backlog_url % page
                data = self.getHTMLData(url, headers = cookie)
                soup = BeautifulSoup(data)

                try:
                    # Stop if the release year is before the minimal year
                    brk = False
                    h3s = soup.body.find_all('h3')
                    for h3 in h3s:
                        if h3.parent.name != 'a':

                            try:
                                page_year = tryInt(h3.get_text()[-4:])
                                if page_year > 0 and page_year < self.getMinimal('year'):
                                    brk = True
                            except:
                                log.error('Failed determining page year: %s', traceback.format_exc())
                                brk = True
                                break

                    if brk:
                        break

                    for h3 in h3s:
                        try:
                            if h3.parent.name == 'a':
                                name = h3.get_text().lower().split('blu-ray')[0].strip()

                                if not name.find('/') == -1:  # make sure it is not a double movie release
                                    continue

                                if not h3.parent.parent.small:  # ignore non-movie tables
                                    continue

                                year = h3.parent.parent.small.get_text().split('|')[1].strip()

                                if tryInt(year) < self.getMinimal('year'):
                                    continue

                                imdb = self.search(name, year)

                                if imdb:
                                    if self.isMinimalMovie(imdb):
                                        movies.append(imdb['imdb'])
                        except:
                            log.debug('Error parsing movie html: %s', traceback.format_exc())
                            break
                except:
                    log.debug('Error loading page %s: %s', (page, traceback.format_exc()))
                    break

            self.conf('backlog', value = False)

        rss_movies = self.getRSSData(self.rss_url)

        for movie in rss_movies:
            name = self.getTextElement(movie, 'title').lower().split('blu-ray')[0].strip('(').rstrip()
            year = self.getTextElement(movie, 'description').split('|')[1].strip('(').strip()

            if not name.find('/') == -1:  # make sure it is not a double movie release
                continue

            if tryInt(year) < self.getMinimal('year'):
                continue

            imdb = self.search(name, year)

            if imdb:
                if self.isMinimalMovie(imdb):
                    movies.append(imdb['imdb'])

        return movies

    def getChartList(self):
        cache_key = 'bluray.charts'
        movie_list = {
            'name': 'Blu-ray.com - New Releases',
            'url': self.display_url,
            'order': self.chart_order,
            'list': self.getCache(cache_key) or []
        }

        if not movie_list['list']:
            movie_ids = []
            max_items = 10
            rss_movies = self.getRSSData(self.rss_url)

            for movie in rss_movies:
                name = self.getTextElement(movie, 'title').lower().split('blu-ray')[0].strip('(').rstrip()
                year = self.getTextElement(movie, 'description').split('|')[1].strip('(').strip()

                if not name.find('/') == -1: # make sure it is not a double movie release
                    continue

                movie = self.search(name, year)

                if movie:

                    if movie.get('imdb') in movie_ids:
                        continue

                    is_movie = fireEvent('movie.is_movie', identifier = movie.get('imdb'), single = True)
                    if not is_movie:
                        continue

                    movie_ids.append(movie.get('imdb'))
                    movie_list['list'].append( movie )
                    if len(movie_list['list']) >= max_items:
                        break

            if not movie_list['list']:
                return

            self.setCache(cache_key, movie_list['list'], timeout = 259200)

        return [movie_list]


config = [{
    'name': 'bluray',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'bluray_automation',
            'label': 'Blu-ray.com',
            'description': 'Imports movies from blu-ray.com.',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'backlog',
                    'advanced': True,
                    'description': ('Parses the history until the minimum movie year is reached. (Takes a while)', 'Will be disabled once it has completed'),
                    'default': False,
                    'type': 'bool',
                },
            ],
        },
        {
            'tab': 'display',
            'list': 'charts_providers',
            'name': 'bluray_charts_display',
            'label': 'Blu-ray.com',
            'description': 'Display <a href="http://www.blu-ray.com/movies/movies.php?show=newreleases" target="_blank">new releases</a> from Blu-ray.com',
            'options': [
                {
                    'name': 'chart_display_enabled',
                    'default': True,
                    'type': 'enabler',
                },
            ],
        },
    ],
}]

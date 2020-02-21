import traceback

import HTMLParser
from bs4 import BeautifulSoup
from couchpotato import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.media.movie.providers.automation.base import Automation

log = CPLog(__name__)

autoload = 'YTSPopular'


class YTSPopular(Automation, RSS):

    interval = 1800
    url = 'https://yts.mx/'
    rss_url = 'https://yts.mx/rss'
    display_url = 'https://yts.mx/'
    chart_order = 2

    def getIMDBids(self):

        movies = []
        source = self.getHTMLData(self.url)

        class MyHTMLParser(HTMLParser):
            doparse = False
            dotitle = False
            doyear = False
            currentmovie = {'title':"", 'year':""}
            movies = []
            def handle_starttag(self, tag, attrs):
                for attr in attrs:
                    self.doparse = (attr[0] == "id" and attr[1] == "popular-downloads") or self.doparse
                    self.dotitle = (attr[0] == "class" and attr[1] == "browse-movie-title" and self.doparse)
                    self.doyear = (attr[0] == "class" and attr[1] == "browse-movie-year" and self.doparse)
                    if (attr[0] == "class" and attr[1] == "home-movies"):
                        self.doparse = False

            def handle_endtag(self, tag):
                self.dotitle = False
                self.doyear = False

            def handle_data(self, data):
                if (self.doparse):
                    if (self.dotitle):
                        self.dotitle = False
                        self.currentmovie['title'] = data
                    if (self.doyear):
                        self.doyear = False
                        self.currentmovie['year'] = data
                        self.movies.append(self.currentmovie)
                        self.currentmovie = {'title':"", 'year':""}

            def getMovies(self):
                return self.movies

        parser = MyHTMLParser()
        parser.feed(source)
        for el in parser.getMovies():
            imdb = self.search(el['title'], el['year'])
            if imdb and self.isMinimalMovie(imdb):
                movies.append(imdb['imdb'])
        
        return movies
    def getChartList(self):
        cache_key = 'yts.charts'
        movie_list = {
            'name': 'YTS - Popular Downloads',
            'url': self.display_url,
            'order': self.chart_order,
            'list': self.getCache(cache_key) or []
        }

        if not movie_list['list']:
            movie_ids = []
            max_items = 10
            rss_movies = self.getRSSData(self.rss_url)

            for movie in rss_movies:
                name = self.getTextElement(movie, 'title').lower()[9:].split("(",1)[0].rstrip()
                year = self.getTextElement(movie, 'title').split("(")[1].split(")")[0].rstrip()

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
    'name': 'ytspopular',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'ytspopular_automation',
            'label': 'YTS Popular',
            'description': 'Imports popular downloads as currently listed on YTS.',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
            ],
        },
        {
            'tab': 'display',
            'list': 'charts_providers',
            'name': 'yts_popular_display',
            'label': 'YTS',
            'description': 'Display <a href="https://yts.mx" target="_blank">Popular Downloads</a> from YTS.MX',
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

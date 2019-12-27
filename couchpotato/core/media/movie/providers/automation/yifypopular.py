import HTMLParser
from couchpotato import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation

log = CPLog(__name__)

autoload = 'YTSPopular'


class YTSPopular(Automation):

    interval = 1800
    url = 'https://yts.lt/'

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
            

config = [{
    'name': 'ytspopular',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'ytspopular_automation',
            'label': 'YTS Popular',
            'description': 'Imports popular downloas as currently listed on YTS.',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
            ],
        },
    ],
}]

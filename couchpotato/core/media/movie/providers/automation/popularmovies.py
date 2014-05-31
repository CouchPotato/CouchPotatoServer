from couchpotato import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation

log = CPLog(__name__)

autoload = 'PopularMovies'


class PopularMovies(Automation):

    interval = 1800
    url = 'https://s3.amazonaws.com/popular-movies/movies.json'

    def getIMDBids(self):

        movies = []
        retrieved_movies = self.getJsonData(self.url)

        for movie in retrieved_movies.get('movies'):
            imdb_id = movie.get('imdb_id')
            info = fireEvent('movie.info', identifier = imdb_id, extended = False, merge = True)
            if self.isMinimalMovie(info):
                movies.append(imdb_id)

        return movies


config = [{
    'name': 'popularmovies',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'popularmovies_automation',
            'label': 'Popular Movies',
            'description': 'Imports the <a href="http://movies.stevenlu.com/">top titles of movies that have been in theaters</a>. Script provided by <a href="https://github.com/sjlu/popular-movies">Steven Lu</a>',
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

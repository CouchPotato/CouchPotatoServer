from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation

log = CPLog(__name__)

autoload = 'Moviemeter'


class Moviemeter(Automation, RSS):

    interval = 1800
    rss_url = 'http://www.moviemeter.nl/rss/cinema'

    def getIMDBids(self):

        movies = []

        rss_movies = self.getRSSData(self.rss_url)

        for movie in rss_movies:
            imdb = self.search(self.getTextElement(movie, 'title'))

            if imdb and self.isMinimalMovie(imdb):
                movies.append(imdb['imdb'])

        return movies


config = [{
    'name': 'moviemeter',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'moviemeter_automation',
            'label': 'Moviemeter',
            'description': 'Imports movies from the current top 10 of moviemeter.nl.',
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

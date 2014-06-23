import datetime

from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation


log = CPLog(__name__)

autoload = 'Kinepolis'


class Kinepolis(Automation, RSS):

    interval = 1800
    rss_url = 'http://kinepolis.be/nl/top10-box-office/feed'

    def getIMDBids(self):

        movies = []

        rss_movies = self.getRSSData(self.rss_url)

        for movie in rss_movies:
            name = self.getTextElement(movie, 'title')
            year = datetime.datetime.now().strftime('%Y')

            imdb = self.search(name, year)

            if imdb and self.isMinimalMovie(imdb):
                movies.append(imdb['imdb'])

        return movies


config = [{
    'name': 'kinepolis',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'kinepolis_automation',
            'label': 'Kinepolis',
            'description': 'Imports movies from the current top 10 of kinepolis.',
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

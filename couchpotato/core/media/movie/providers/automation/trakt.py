import base64

from couchpotato.core.event import addEvent
from couchpotato.core.helpers.variable import sha1
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation


log = CPLog(__name__)

autoload = 'Trakt'


class Trakt(Automation):

    urls = {
        'base': 'https://api-v2launch.trakt.tv/',
        'watchlist': 'sync/watchlist/movies/',
    }

    def __init__(self):
        super(Trakt, self).__init__()

    def getIMDBids(self):
        movies = []
        for movie in self.getWatchlist():
            movies.append(movie.get('movie').get('ids').get('imdb'))

        return movies

    def getWatchlist(self):
        method = self.urls['watchlist']
        return self.call(method)

    def call(self, method_url):
        headers = {}
        headers['Authorization'] = 'Bearer %s' % self.conf('automation_api_key')
        headers['trakt-api-version'] = 2
        headers['trakt-api-key'] = self.conf('automation_client_id')

        data = self.getJsonData(self.urls['base'] + method_url, headers = headers)
        return data if data else []


config = [{
    'name': 'trakt',
    'groups': [
        {
            'tab': 'automation',
            'list': 'watchlist_providers',
            'name': 'trakt_automation',
            'label': 'Trakt',
            'description': 'Import movies from your own watchlist',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_api_key',
                    'label': 'ApiKey',
                    'description': 'Create a new PIN authentication application <a href="http://trakt.tv/oauth/applications">on trakt</a>, and <a href="http://docs.trakt.apiary.io/#reference/authentication-pin">exchange the PIN for a token</a>.'
                },
                {
                    'name': 'automation_client_id',
                    'label': 'ClientID'
                },
            ],
        },
    ],
}]

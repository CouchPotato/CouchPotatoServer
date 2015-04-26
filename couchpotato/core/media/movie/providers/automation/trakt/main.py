from couchpotato import Env
from couchpotato.api import addApiView
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation


log = CPLog(__name__)


class Trakt(Automation):

    client_id = '8a54ed7b5e1b56d874642770ad2e8b73e2d09d6e993c3a92b1e89690bb1c9014'

    urls = {
        'base': 'https://api-v2launch.trakt.tv/',
        'watchlist': 'sync/watchlist/movies/',
        'oauth': 'https://api.couchpota.to/authorize/trakt/',
    }

    def __init__(self):
        addApiView('automation.trakt.auth_url', self.getAuthorizationUrl)
        addApiView('automation.trakt.credentials', self.getCredentials)

        super(Trakt, self).__init__()

    def getIMDBids(self):
        movies = []
        for movie in self.getWatchlist():
            movies.append(movie.get('movie').get('ids').get('imdb'))

        return movies

    def getWatchlist(self):
        return self.call(self.urls['watchlist'])

    def getAuthorizationUrl(self, host = None, **kwargs):
        callback_url = cleanHost(host) + '%sautomation.trakt.credentials/' % (Env.get('api_base').lstrip('/'))
        log.debug('callback_url is %s', callback_url)

        target_url = self.urls['oauth'] + "?target=" + callback_url
        log.debug('target_url is %s', target_url)

        return {
            'success': True,
            'url': target_url,
        }

    def getCredentials(self, **kwargs):
        try:
            oauth_token = kwargs.get('oauth')
        except:
            return 'redirect', Env.get('web_base') + 'settings/automation/'
        log.debug('oauth_token is: %s', oauth_token)
        self.conf('automation_oauth_token', value = oauth_token)
        return 'redirect', Env.get('web_base') + 'settings/automation/'

    def call(self, method_url):
        headers = {
            'Authorization': 'Bearer %s' % self.conf('automation_oauth_token'),
            'trakt-api-version': 2,
            'trakt-api-key': self.client_id,
        }

        data = self.getJsonData(self.urls['base'] + method_url, headers = headers)
        return data if data else []


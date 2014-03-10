from couchpotato.core.event import addEvent
from couchpotato.core.helpers.variable import sha1
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import base64

log = CPLog(__name__)


class Trakt(Automation):

    urls = {
        'base': 'http://api.trakt.tv/',
        'watchlist': 'user/watchlist/movies.json/%s/',
    }

    def __init__(self):
        super(Trakt, self).__init__()

        addEvent('setting.save.trakt.automation_password', self.sha1Password)

    def sha1Password(self, value):
        return sha1(value) if value else ''

    def getIMDBids(self):

        movies = []
        for movie in self.getWatchlist():
            movies.append(movie.get('imdb_id'))

        return movies

    def getWatchlist(self):
        method = (self.urls['watchlist'] % self.conf('automation_api_key')) + self.conf('automation_username')
        return self.call(method)

    def call(self, method_url):

        headers = {}
        if self.conf('automation_password'):
            headers['Authorization'] = 'Basic %s' % base64.encodestring('%s:%s' % (self.conf('automation_username'), self.conf('automation_password')))[:-1]

        data = self.getJsonData(self.urls['base'] + method_url, headers = headers)
        return data if data else []

from couchpotato.core.helpers.variable import md5
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import json

log = CPLog(__name__)


class Trakt(Automation):

    urls = {
        'base': 'http://api.trakt.tv/',
        'watchlist': 'user/watchlist/movies.json/%s/',
    }

    def getIMDBids(self):

        if self.isDisabled():
            return

        movies = []
        for movie in self.getWatchlist():
            movies.append(movie.get('imdb_id'))

        return movies

    def getWatchlist(self):
        method = (self.urls['watchlist'] % self.conf('automation_api_key')) + self.conf('automation_username')
        return self.call(method)


    def call(self, method_url):

        cache_key = 'trakt.%s' % md5(method_url)
        json_string = self.getCache(cache_key, self.urls['base'] + method_url)
        return json.loads(json_string)

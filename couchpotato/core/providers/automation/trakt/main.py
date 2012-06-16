from couchpotato.core.event import addEvent
from couchpotato.core.helpers.variable import md5, sha1
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import base64
import json

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

        try:
            if self.conf('automation_password'):
                headers = {
                   'Authorization': 'Basic %s' % base64.encodestring('%s:%s' % (self.conf('automation_username'), self.conf('automation_password')))[:-1]
                }
            else:
                headers = {}

            cache_key = 'trakt.%s' % md5(method_url)
            json_string = self.getCache(cache_key, self.urls['base'] + method_url, headers = headers)
            if json_string:
                return json.loads(json_string)
        except:
            log.error('Failed to get data from trakt, check your login.')

        return []

from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import json
import urllib2

log = CPLog(__name__)

class Trakt(Notification):

    urls = {
        'base': 'http://api.trakt.tv/',
        'library': 'movie/library/%s',
        'unwatchlist': 'movie/unwatchlist/%s',
    }

    listen_to = ['movie.downloaded']

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return
        if not data: return
        post_data = {
            'username': self.conf('automation_username'),
            'password' : self.conf('automation_password'),
            'movies': [ {
                'imdb_id': data['library']['identifier'],
                'title': data['library']['titles'][0]['title'],
                'year': data['library']['year']
                } ]
            }
        result = False
        result = self.call((self.urls['library'] % self.conf('automation_api_key')), post_data)
        if self.conf('remove_watchlist_enabled'):
            result = result and self.call((self.urls['unwatchlist'] % self.conf('automation_api_key')), post_data)

        return result

    def call(self, method_url, post_data):
        log.info('opening url: ' + self.urls['base'] + method_url + ', post: ' + str(post_data))
        try:
            response = urllib2.urlopen(self.urls['base'] + method_url, json.dumps(post_data))
            if response:
                if json.load(response).get('status') == "success":
                    log.info('Successfully called Trakt')
                    return True
        except:
            pass
        log.error('Failed to call trakt, check your login.')
        return False
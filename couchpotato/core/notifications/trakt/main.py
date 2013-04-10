from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification

log = CPLog(__name__)

class Trakt(Notification):

    urls = {
        'base': 'http://api.trakt.tv/%s',
        'library': 'movie/library/%s',
        'unwatchlist': 'movie/unwatchlist/%s',
    }

    listen_to = ['movie.downloaded']

    def notify(self, message = '', data = {}, listener = None):

        post_data = {
            'username': self.conf('automation_username'),
            'password' : self.conf('automation_password'),
            'movies': [{
                'imdb_id': data['library']['identifier'],
                'title': data['library']['titles'][0]['title'],
                'year': data['library']['year']
            }] if data else []
        }

        result = self.call((self.urls['library'] % self.conf('automation_api_key')), post_data)
        if self.conf('remove_watchlist_enabled'):
            result = result and self.call((self.urls['unwatchlist'] % self.conf('automation_api_key')), post_data)

        return result

    def call(self, method_url, post_data):

        try:
            response = self.getJsonData(self.urls['base'] % method_url, params = post_data, cache_timeout = 1)
            if response:
                if response.get('status') == "success":
                    log.info('Successfully called Trakt')
                    return True
        except:
            pass

        log.error('Failed to call trakt, check your login.')
        return False

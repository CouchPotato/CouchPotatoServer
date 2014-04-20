from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification

log = CPLog(__name__)

autoload = 'Trakt'


class Trakt(Notification):

    urls = {
        'base': 'http://api.trakt.tv/%s',
        'library': 'movie/library/%s',
        'unwatchlist': 'movie/unwatchlist/%s',
        'test': 'account/test/%s',
    }

    listen_to = ['movie.downloaded']

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        if listener == 'test':

            post_data = {
                'username': self.conf('automation_username'),
                'password': self.conf('automation_password'),
            }

            result = self.call((self.urls['test'] % self.conf('automation_api_key')), post_data)

            return result

        else:

            post_data = {
                'username': self.conf('automation_username'),
                'password': self.conf('automation_password'),
                'movies': [{
                    'imdb_id': data['identifier'],
                    'title': getTitle(data),
                    'year': data['info']['year']
                }] if data else []
            }

            result = self.call((self.urls['library'] % self.conf('automation_api_key')), post_data)
            if self.conf('remove_watchlist_enabled'):
                result = result and self.call((self.urls['unwatchlist'] % self.conf('automation_api_key')), post_data)

            return result

    def call(self, method_url, post_data):

        try:

            response = self.getJsonData(self.urls['base'] % method_url, data = post_data, cache_timeout = 1)
            if response:
                if response.get('status') == "success":
                    log.info('Successfully called Trakt')
                    return True
        except:
            pass

        log.error('Failed to call trakt, check your login.')
        return False


config = [{
    'name': 'trakt',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'trakt',
            'label': 'Trakt',
            'description': 'add movies to your collection once downloaded. Fill in your username and password in the <a href="../automation/">Automation Trakt settings</a>',
            'options': [
                {
                    'name': 'notification_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'remove_watchlist_enabled',
                    'label': 'Remove from watchlist',
                    'default': False,
                    'type': 'bool',
                },
            ],
        }
    ],
}]

from couchpotato.core.helpers.variable import getTitle, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.trakt.main import TraktBase
from couchpotato.core.notifications.base import Notification

log = CPLog(__name__)

autoload = 'Trakt'


class Trakt(Notification, TraktBase):

    urls = {
        'library': 'sync/collection',
        'unwatchlist': 'sync/watchlist/remove',
        'test': 'sync/last_activities',
    }

    listen_to = ['renamer.after']
    enabled_option = 'notification_enabled'

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        if listener == 'test':
            result = self.call((self.urls['test']))

            return result

        else:

            post_data = {
                'movies': [{'ids': {'imdb': getIdentifier(data)}}] if data else []
            }

            result = self.call((self.urls['library']), post_data)
            if self.conf('remove_watchlist_enabled'):
                result = result and self.call((self.urls['unwatchlist']), post_data)

            return result


config = [{
    'name': 'trakt',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'trakt',
            'label': 'Trakt',
            'description': 'add movies to your collection once downloaded. Connect your account in <a href="../automation/">Automation Trakt settings</a>',
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

import traceback

from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getIdentifier, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification

log = CPLog(__name__)

autoload = 'Homey'

class Homey(Notification):

    listen_to = [
        'media.available',
        'renamer.after', 'movie.snatched',
    ]

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        url = self.conf('url')

        if not url:
            log.error('Please provide the URL')
            return False

        post_data = {
            'type': listener,
            'movie': getTitle(data) if listener != 'test' else 'Test Movie Title (2016)',
            'message': toUnicode(message)
        }

        try:
            self.urlopen(url, data = post_data, show_error = False)
            return True
        except:
            log.error('Webhook notification failed: %s', traceback.format_exc())

        return False


config = [{
    'name': 'homey',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'homey',
            'label': 'Homey',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'url',
                    'description': 'Create a new one at <a href="https://webhooks.athom.com/" target="_blank">webhooks.athom.com</a> and add to to Homey Settings'
                }
            ]
        }
    ]
}]

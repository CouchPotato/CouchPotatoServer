import traceback

from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification


log = CPLog(__name__)

autoload = 'Pushalot'


class Pushalot(Notification):

    urls = {
        'api': 'https://pushalot.com/api/sendmessage'
    }

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        data = {
            'AuthorizationToken': self.conf('auth_token'),
            'Title': self.default_title,
            'Body': toUnicode(message),
            'IsImportant': self.conf('important'),
            'IsSilent': self.conf('silent'),
            'Image': toUnicode(self.getNotificationImage('medium') + '?1'),
            'Source': toUnicode(self.default_title)
        }

        headers = {
            'Content-type': 'application/x-www-form-urlencoded'
        }

        try:
            self.urlopen(self.urls['api'], headers = headers, data = data, show_error = False)
            return True
        except:
            log.error('PushAlot failed: %s', traceback.format_exc())

        return False


config = [{
    'name': 'pushalot',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'pushalot',
            'description': 'for Windows Phone and Windows 8',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'auth_token',
                    'label': 'Auth Token',
                },
                {
                    'name': 'silent',
                    'label': 'Silent',
                    'default': 0,
                    'type': 'bool',
                    'description': 'Don\'t send Toast notifications. Only update Live Tile',
                },
                {
                    'name': 'important',
                    'label': 'High Priority',
                    'default': 0,
                    'type': 'bool',
                    'description': 'Send message with High priority.',
                },
                {
                    'name': 'on_snatch',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
            ],
        }
    ],
}]

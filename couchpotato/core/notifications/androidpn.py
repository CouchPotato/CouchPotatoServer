import traceback

from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification


log = CPLog(__name__)

autoload = 'AndroidPN'


class AndroidPN(Notification):

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        data = {
            'action': "send",
            'uri': "",
            'title': self.default_title,
            'message': toUnicode(message),
            'broadcast': self.conf('broadcast'),
            'username': self.conf('username'),
        }

        headers = {
            'Content-type': 'application/x-www-form-urlencoded'
        }

        try:
            self.urlopen(self.conf('url'), headers = headers, data = data, show_error = False)
            return True
        except:
            log.error('AndroidPN failed: %s', traceback.format_exc())

        return False


config = [{
    'name': 'androidpn',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'androidpn',
            'description': 'Self hosted Android push notification server',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'broadcast',
                    'label': 'Broadcast',
                    'default': 1,
                    'type': 'bool',
                    'description': 'Send notification to all users',
                },
                {
                    'name': 'username',
                    'label': 'Username',
                    'description': 'Required if broadcast not selected',
                },
                {
                    'name': 'url',
                    'label': 'Url',
                    'description': 'URL of server',
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

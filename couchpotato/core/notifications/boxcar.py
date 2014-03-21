import time

from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification


log = CPLog(__name__)

autoload = 'Boxcar'


class Boxcar(Notification):

    url = 'https://boxcar.io/devices/providers/7MNNXY3UIzVBwvzkKwkC/notifications'

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        try:
            message = message.strip()

            data = {
                'email': self.conf('email'),
                'notification[from_screen_name]': self.default_title,
                'notification[message]': toUnicode(message),
                'notification[from_remote_service_id]': int(time.time()),
            }

            self.urlopen(self.url, data = data)
        except:
            log.error('Check your email and added services on boxcar.io')
            return False

        log.info('Boxcar notification successful.')
        return True

    def isEnabled(self):
        return super(Boxcar, self).isEnabled() and self.conf('email')


config = [{
    'name': 'boxcar',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'boxcar',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'email',
                    'description': 'Your Boxcar registration emailaddress.'
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

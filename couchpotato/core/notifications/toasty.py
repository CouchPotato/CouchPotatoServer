import traceback

from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification


log = CPLog(__name__)

autoload = 'Toasty'


class Toasty(Notification):

    urls = {
        'api': 'http://api.supertoasty.com/notify/%s?%s'
    }

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        data = {
            'title': self.default_title,
            'text': toUnicode(message),
            'sender': toUnicode("CouchPotato"),
            'image': 'https://raw.github.com/CouchPotato/CouchPotatoServer/master/couchpotato/static/images/homescreen.png',
        }

        try:
            self.urlopen(self.urls['api'] % (self.conf('api_key'), tryUrlencode(data)), show_error = False)
            return True
        except:
            log.error('Toasty failed: %s', traceback.format_exc())

        return False


config = [{
    'name': 'toasty',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'toasty',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'api_key',
                    'label': 'Device ID',
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

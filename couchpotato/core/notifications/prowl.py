import traceback

from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification


log = CPLog(__name__)

autoload = 'Prowl'


class Prowl(Notification):

    urls = {
        'api': 'https://api.prowlapp.com/publicapi/add'
    }

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        data = {
            'apikey': self.conf('api_key'),
            'application': self.default_title,
            'description': toUnicode(message),
            'priority': self.conf('priority'),
        }
        headers = {
            'Content-type': 'application/x-www-form-urlencoded'
        }

        try:
            self.urlopen(self.urls['api'], headers = headers, data = data, show_error = False)
            log.info('Prowl notifications sent.')
            return True
        except:
            log.error('Prowl failed: %s', traceback.format_exc())

        return False


config = [{
    'name': 'prowl',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'prowl',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'api_key',
                    'label': 'Api key',
                },
                {
                    'name': 'priority',
                    'default': '0',
                    'type': 'dropdown',
                    'values': [('Very Low', -2), ('Moderate', -1), ('Normal', 0), ('High', 1), ('Emergency', 2)]
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

from httplib import HTTPSConnection

from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification


log = CPLog(__name__)

autoload = 'Pushover'


class Pushover(Notification):

    app_token = 'YkxHMYDZp285L265L3IwH3LmzkTaCy'

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        http_handler = HTTPSConnection("api.pushover.net:443")

        api_data = {
            'user': self.conf('user_key'),
            'token': self.app_token,
            'message': toUnicode(message),
            'priority': self.conf('priority'),
            'sound': self.conf('sound'),
        }

        if data and data.get('identifier'):
            api_data.update({
                'url': toUnicode('http://www.imdb.com/title/%s/' % data['identifier']),
                'url_title': toUnicode('%s on IMDb' % getTitle(data)),
            })

        http_handler.request('POST', '/1/messages.json',
                             headers = {'Content-type': 'application/x-www-form-urlencoded'},
                             body = tryUrlencode(api_data)
        )

        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
            log.info('Pushover notifications sent.')
            return True
        elif request_status == 401:
            log.error('Pushover auth failed: %s', response.reason)
            return False
        else:
            log.error('Pushover notification failed.')
            return False


config = [{
    'name': 'pushover',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'pushover',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'user_key',
                    'description': 'Register on pushover.net to get one.'
                },
                {
                    'name': 'priority',
                    'default': 0,
                    'type': 'dropdown',
                    'values': [('Normal', 0), ('High', 1)],
                },
                {
                    'name': 'on_snatch',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
                {
                    'name': 'sound',
                    'advanced': True,
                    'description': 'Define <a href="https://pushover.net/api%23sounds" target="_blank">custom sound</a> for Pushover alert.'
                },
            ],
        }
    ],
}]

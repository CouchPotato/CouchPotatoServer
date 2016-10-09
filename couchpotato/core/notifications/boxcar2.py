from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification

log = CPLog(__name__)

autoload = 'Boxcar2'


class Boxcar2(Notification):

    url = 'https://new.boxcar.io/api/notifications'
    LOGO_URL = 'https://raw.githubusercontent.com/CouchPotato/CouchPotatoServer/master/couchpotato/static/images/notify.couch.small.png'

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        try:
            message = message.strip()

            long_message = ''
            if listener == 'test':
                long_message = 'This is a test message'
            elif data.get('identifier'):
                long_message = 'More movie info <a href="http://www.imdb.com/title/%s/">on IMDB</a>' % data['identifier']

            data = {
                'user_credentials': self.conf('token'),
                'notification[title]': toUnicode('%s - %s' % (self.default_title, message)),
                'notification[long_message]': toUnicode(long_message),
                'notification[icon_url]': self.LOGO_URL,
                'notification[source_name]': 'CouchPotato',
            }

            self.urlopen(self.url, data = data)
        except:
            log.error('Make sure the token provided is for the correct device')
            return False

        log.info('Boxcar notification successful.')
        return True

    def isEnabled(self):
        return super(Boxcar2, self).isEnabled() and self.conf('token')


config = [{
    'name': 'boxcar2',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'boxcar2',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'token',
                    'description': ('Your Boxcar access token.', 'Can be found in the app under settings')
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

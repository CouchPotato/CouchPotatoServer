from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification

log = CPLog(__name__)


class Boxcar2(Notification):

    url = 'https://new.boxcar.io/api/notifications'

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
                'notification[title]': toUnicode(message),
                'notification[long_message]': toUnicode(long_message),
            }

            self.urlopen(self.url, data = data)
        except:
            log.error('Make sure the token provided is for the correct device')
            return False

        log.info('Boxcar notification successful.')
        return True

    def isEnabled(self):
        return super(Boxcar2, self).isEnabled() and self.conf('token')

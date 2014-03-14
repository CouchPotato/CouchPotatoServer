from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import time

log = CPLog(__name__)


class Boxcar2(Notification):

    url = "https://new.boxcar.io/api/notifications"

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        try:
            message = message.strip()

            data = {
                'user_credentials': self.conf('accessToken'),
                'notification[title]': self.default_title + " - " + toUnicode(message),
                'notification[long_message]': toUnicode(message),
                'notification[sound]': "done"
            }

            self.urlopen(self.url, data = data)
        except:
            log.error('Check your Access Token in the Boxcar2 App')
            return False

        log.info('Boxcar2 notification successful.')
        return True

    def isEnabled(self):
        return super(Boxcar2, self).isEnabled() and self.conf('accessToken')

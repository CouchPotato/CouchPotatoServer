from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import traceback

log = CPLog(__name__)

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

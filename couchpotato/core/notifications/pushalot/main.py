from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import traceback

log = CPLog(__name__)

class Pushalot(Notification):

    urls = {
        'api': 'https://pushalot.com/api/sendmessage'
    }

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        data = {
            'AuthorizationToken': self.conf('auth_token'),
            'Title': self.default_title,
            'Body': toUnicode(message),
            'LinkTitle': toUnicode("CouchPotato"),
            'link': toUnicode("https://couchpota.to/"),
            'IsImportant': self.conf('important'),
            'IsSilent': self.conf('silent'),
        }

        headers = {
           'Content-type': 'application/x-www-form-urlencoded'
        }

        try:
            self.urlopen(self.urls['api'], headers = headers, params = data, multipart = True, show_error = False)
            return True
        except:
            log.error('PushAlot failed: %s', traceback.format_exc())

        return False

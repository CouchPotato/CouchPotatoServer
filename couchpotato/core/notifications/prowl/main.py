from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import traceback

log = CPLog(__name__)


class Prowl(Notification):

    urls = {
        'api': 'https://api.prowlapp.com/publicapi/add'
    }

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

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
            self.urlopen(self.urls['api'], headers = headers, params = data, multipart = True, show_error = False)
            log.info('Prowl notifications sent.')
            return True
        except:
            log.error('Prowl failed: %s', traceback.format_exc())

        return False

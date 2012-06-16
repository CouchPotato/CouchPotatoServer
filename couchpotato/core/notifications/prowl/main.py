from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from httplib import HTTPSConnection

log = CPLog(__name__)


class Prowl(Notification):

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        http_handler = HTTPSConnection('api.prowlapp.com')

        data = {
            'apikey': self.conf('api_key'),
            'application': self.default_title,
            'description': toUnicode(message),
            'priority': self.conf('priority'),
        }

        http_handler.request('POST',
            '/publicapi/add',
            headers = {'Content-type': 'application/x-www-form-urlencoded'},
            body = tryUrlencode(data)
        )
        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
            log.info('Prowl notifications sent.')
            return True
        elif request_status == 401:
            log.error('Prowl auth failed: %s', response.reason)
            return False
        else:
            log.error('Prowl notification failed.')
            return False

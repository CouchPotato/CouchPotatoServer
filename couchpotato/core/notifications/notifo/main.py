from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import base64
import json
import traceback

log = CPLog(__name__)


class Notifo(Notification):

    url = 'https://api.notifo.com/v1/send_notification'

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        try:
            params = {
                'label': self.default_title,
                'msg': toUnicode(message),
            }

            headers = {
                'Authorization': "Basic %s" % base64.encodestring('%s:%s' % (self.conf('username'), self.conf('api_key')))[:-1]
            }

            handle = self.urlopen(self.url, params = params, headers = headers)
            result = json.loads(handle)

            if result['status'] != 'success' or result['response_message'] != 'OK':
                raise Exception

        except:
            log.error('Notification failed: %s', traceback.format_exc())
            return False

        log.info('Notifo notification successful.')
        return True

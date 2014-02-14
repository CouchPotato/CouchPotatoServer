from couchpotato.core.helpers.variable import splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import pynma
import six

log = CPLog(__name__)


class NotifyMyAndroid(Notification):

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        nma = pynma.PyNMA()
        keys = splitString(self.conf('api_key'))
        nma.addkey(keys)
        nma.developerkey(self.conf('dev_key'))

        response = nma.push(
            application = self.default_title,
            event = message.split(' ')[0],
            description = message,
            priority = self.conf('priority'),
            batch_mode = len(keys) > 1
        )

        successful = 0
        for key in keys:
            if not response[str(key)]['code'] == six.u('200'):
                log.error('Could not send notification to NotifyMyAndroid (%s). %s', (key, response[key]['message']))
            else:
                successful += 1

        return successful == len(keys)

from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import pynma

log = CPLog(__name__)


class NotifyMyAndroid(Notification):

    def notify(self, message = '', data = {}):
        if self.isDisabled(): return

        nma = pynma.PyNMA()
        keys = self.conf('api_key').split(',')
        nma.addkey(keys)
        nma.developerkey(self.conf('dev_key'))

        response = nma.push(self.app_name, 'CouchPotato', message, priority = self.priority, batch_mode = len(keys) > 1)

        for key in keys:
            if not response[str(key)]['code'] == u'200':
                log.error('Could not send notification to NotifyMyAndroid (%s). %s' % (key, response[key]['message']))

        return response

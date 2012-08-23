from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import pynma

log = CPLog(__name__)


class NotifyMyAndroid(Notification):

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        nma = pynma.PyNMA()
        keys = [x.strip() for x in self.conf('api_key').split(',')]
        nma.addkey(keys)
        nma.developerkey(self.conf('dev_key'))

        # hacky fix for the event type 
        # as it seems to be part of the message now
        self.event = message.split(' ')[0]

        response = nma.push(self.default_title, self.event , message, self.conf('priority'), batch_mode = len(keys) > 1)

        successful = 0
        for key in keys:
            if not response[str(key)]['code'] == u'200':
                log.error('Could not send notification to NotifyMyAndroid (%s). %s', (key, response[key]['message']))
            else:
                successful += 1

        return successful == len(keys)
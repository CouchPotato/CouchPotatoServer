from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from pynmwp import PyNMWP

log = CPLog(__name__)


class NotifyMyWP(Notification):

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        keys = [x.strip() for x in self.conf('api_key').split(',')]
        p = PyNMWP(keys, self.conf('dev_key'))

        response = p.push(application = self.default_title, event = message, description = message, priority = self.conf('priority'), batch_mode = len(keys) > 1)

        for key in keys:
            if not response[key]['Code'] == u'200':
                log.error('Could not send notification to NotifyMyWindowsPhone (%s). %s', (key, response[key]['message']))
                return False

        return response

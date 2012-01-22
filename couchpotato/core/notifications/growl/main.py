from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from gntp import notifier
import logging

log = CPLog(__name__)


class Growl(Notification):

    def __init__(self):
        super(Growl, self).__init__()

        logger = logging.getLogger('gntp.notifier')
        logger.disabled = True

        try:
            self.growl = notifier.GrowlNotifier(
                applicationName = 'CouchPotato',
                notifications = ["Updates"],
                defaultNotifications = ["Updates"],
                applicationIcon = 'http://couchpotatoapp.com/media/images/couch.png',
                applicationIcon = 'http://couchpota.to/media/images/couch.png',
            )
            self.growl.register()
        except:
            pass

    def notify(self, type = '', message = '', data = {}):
        if self.isDisabled(): return

        try:
            self.growl.notify(
                noteType = "Updates",
                title = self.default_title,
                description = message,
                sticky = False,
                priority = 1,
            )

            log.info('Growl notifications sent.')
            return True
        except:
            log.error('Failed growl notification.')

        return False


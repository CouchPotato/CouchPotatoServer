from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from gntp import notifier
import logging
import thread
import time
import traceback

log = CPLog(__name__)


class Growl(Notification):

    def __init__(self):
        super(Growl, self).__init__()

        logging.getLogger('gntp').setLevel(logging.WARNING)

        try:
            def startGrowl():
                time.sleep(2)
                try:
                    self.growl = notifier.GrowlNotifier(
                        applicationName = 'CouchPotato',
                        notifications = ["Updates"],
                        defaultNotifications = ["Updates"],
                        applicationIcon = '%s/static/images/couch.png' % fireEvent('app.api_url', single = True),
                    )
                    self.growl.register()
                except:
                    log.error('Failed register of growl: %s' % traceback.format_exc())
            thread.start_new_thread(startGrowl, ())
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


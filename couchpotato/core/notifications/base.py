from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.request import jsonified
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class Notification(Plugin):

    default_title = 'CouchPotato'
    test_message = 'ZOMG Lazors Pewpewpew!'

    listen_to = ['movie.downloaded', 'movie.snatched', 'updater.available']
    dont_listen_to = []

    def __init__(self):
        addEvent('notify.%s' % self.getName().lower(), self.notify)

        addApiView(self.testNotifyName(), self.test)

        # Attach listeners
        for listener in self.listen_to:
            if not listener in self.dont_listen_to:
                addEvent(listener, self.createNotifyHandler(listener))

    def createNotifyHandler(self, listener):
        def notify(message, data):
            if not self.conf('on_snatch', default = True) and listener == 'movie.snatched':
                return
            return self.notify(message = message, data = data)

        return notify

    def notify(self, message = '', data = {}):
        pass

    def test(self):

        test_type = self.testNotifyName()

        log.info('Sending test to %s' % test_type)

        success = self.notify(
            message = self.test_message,
            data = {}
        )

        return jsonified({'success': success})

    def testNotifyName(self):
        return 'notify.%s.test' % self.getName().lower()

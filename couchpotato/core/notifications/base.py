from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.request import jsonified
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class Notification(Plugin):

    default_title = 'CouchPotato'
    test_message = 'ZOMG Lazors Pewpewpew!'

    listen_to = []
    dont_listen_to = []

    def __init__(self):
        addEvent('notify', self.notify)
        addEvent('notify.%s' % self.getName().lower(), self.notify)

        addApiView(self.testNotifyName(), self.test)

    def notify(self, message = '', data = {}, type = ''):
        pass

    def test(self):

        test_type = self.testNotifyName()

        log.info('Sending test to %s' % test_type)

        success = self.notify(
            message = self.test_message,
            data = {},
            type = test_type
        )

        #return jsonified({'success': success})

    def dontNotify(self, type = ''):
        return (not type in self.listen_to and len(self.listen_to) == 0 and type != self.testNotifyName()) \
            or type in self.dont_listen_to \
            or self.isDisabled()

    def testNotifyName(self):
        return 'notify.%s.test' % self.getName().lower()

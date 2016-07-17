from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.base import Provider
from couchpotato.environment import Env

log = CPLog(__name__)


class Notification(Provider):

    type = 'notification'

    default_title = Env.get('appname')
    test_message = 'ZOMG Lazors Pewpewpew!'

    listen_to = [
        'media.available',
        'renamer.after', 'movie.snatched',
        'updater.available', 'updater.updated',
        'core.message.important',
    ]
    dont_listen_to = []

    def __init__(self):
        addEvent('notify.%s' % self.getName().lower(), self._notify)

        addApiView(self.testNotifyName(), self.test)

        # Attach listeners
        for listener in self.listen_to:
            if not listener in self.dont_listen_to:
                addEvent(listener, self.createNotifyHandler(listener))

    def createNotifyHandler(self, listener):
        def notify(message = None, group = None, data = None):
            if not group: group = {}

            if not self.conf('on_snatch', default = True) and listener == 'movie.snatched':
                return
            return self._notify(message = message, data = data if data else group, listener = listener)

        return notify

    def getNotificationImage(self, size = 'small'):
        return 'https://raw.github.com/CouchPotato/CouchPotatoServer/master/couchpotato/static/images/notify.couch.%s.png' % size

    def _notify(self, *args, **kwargs):
        if self.isEnabled():
            return self.notify(*args, **kwargs)
        return False

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

    def test(self, **kwargs):

        test_type = self.testNotifyName()

        log.info('Sending test to %s', test_type)

        success = self._notify(
            message = self.test_message,
            data = {},
            listener = 'test'
        )

        return {
            'success': success
        }

    def testNotifyName(self):
        return 'notify.%s.test' % self.getName().lower()

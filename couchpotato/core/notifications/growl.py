import traceback

from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from couchpotato.environment import Env
from gntp import notifier


log = CPLog(__name__)

autoload = 'Growl'


class Growl(Notification):

    registered = False

    def __init__(self):
        super(Growl, self).__init__()

        self.growl = None

        if self.isEnabled():
            addEvent('app.load', self.register)

    def register(self):
        if self.registered: return
        try:

            hostname = self.conf('hostname')
            password = self.conf('password')
            port = self.conf('port')

            self.growl = notifier.GrowlNotifier(
                applicationName = Env.get('appname'),
                notifications = ["Updates"],
                defaultNotifications = ["Updates"],
                applicationIcon = '%s/static/images/couch.png' % fireEvent('app.api_url', single = True),
                hostname = hostname if hostname else 'localhost',
                password = password if password else None,
                port = port if port else 23053
            )
            self.growl.register()
            self.registered = True
        except Exception as e:
            if 'timed out' in str(e):
                self.registered = True
            else:
                log.error('Failed register of growl: %s', traceback.format_exc())

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        self.register()

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


config = [{
    'name': 'growl',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'growl',
            'description': 'Version 1.4+',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'on_snatch',
                    'default': False,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
                {
                    'name': 'hostname',
                    'description': 'Notify growl over network. Needs restart.',
                    'advanced': True,
                },
                {
                    'name': 'port',
                    'type': 'int',
                    'advanced': True,
                },
                {
                    'name': 'password',
                    'type': 'password',
                    'advanced': True,
                },
            ],
        }
    ],
}]

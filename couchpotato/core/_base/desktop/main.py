from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env

log = CPLog(__name__)

if Env.get('desktop'):

    class Desktop(Plugin):

        def __init__(self):

            desktop = Env.get('desktop')
            desktop.setSettings({
                'base_url': fireEvent('app.base_url', single = True),
                'api_url': fireEvent('app.api_url', single = True),
                'api': Env.setting('api'),
            })

            # Events from desktop
            desktop.addEvents({
                'onClose': self.onClose,
            })

            # Events to desktop
            addEvent('app.after_shutdown', desktop.afterShutdown)
            addEvent('app.load', desktop.onAppLoad, priority = 110)

        def onClose(self, event):
            return fireEvent('app.shutdown', single = True)

else:

    class Desktop(Plugin):
        pass

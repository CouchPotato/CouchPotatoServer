from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env

log = CPLog(__name__)

if Env.get('desktop'):

    #import os
    #import sys
    import wx

    class Desktop(Plugin):

        def __init__(self):

            desktop = Env.get('desktop')
            desktop.setSettings({
                'url': fireEvent('app.base_url', single = True)
            })

            def onClose(event):
                return fireEvent('app.crappy_shutdown')
            desktop.close_handler = onClose

            addEvent('app.after_shutdown', desktop.afterShutdown)

else:

    class Desktop(Plugin):
        pass

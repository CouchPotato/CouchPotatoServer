from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.request import jsonified
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import time

log = CPLog(__name__)


class CoreNotifier(Notification):

    messages = []

    def __init__(self):

        addEvent('notify', self.notify)
        addEvent('notify.frontend', self.frontend)

        addApiView('core_notifier.listener', self.listener)

        self.registerEvents()


    def registerEvents(self):

        # Library update, frontend refresh
        def onLibraryUpdate(data):
            fireEvent('notify.frontend', type = 'library.update', data = data)
        addEvent('library.update', onLibraryUpdate)

    def notify(self, message = '', data = {}, type = None):
        self.add(data = {
            'message': message,
            'raw': data,
        })

    def frontend(self, type = 'notification', data = {}):
        self.messages.append({
            'time': time.time(),
            'type': type,
            'data': data,
        })

    def listener(self):

        messages = []
        for message in self.messages:
            #delete message older then 15s
            if message['time'] > (time.time() - 15):
                messages.append(message)

        self.messages = []
        return jsonified({
            'success': True,
            'result': messages,
        })

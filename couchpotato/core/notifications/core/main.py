from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.request import jsonified
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
import time

log = CPLog(__name__)


class CoreNotifier(Plugin):

    messages = []

    def __init__(self):
        addEvent('notify', self.notify)
        addEvent('notify.core_notifier', self.notify)
        addEvent('core_notifier.frontend', self.frontend)

        addApiView('core_notifier.listener', self.listener)

        static = self.registerStatic(__file__)
        fireEvent('register_script', static + 'notification.js')

    def notify(self, message = '', data = {}):
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

        for message in self.messages:
            #delete message older then 15s
            if message['time'] < (time.time() - 15):
                del message

        return jsonified({
            'success': True,
            'result': self.messages,
        })

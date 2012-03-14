from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.request import jsonified, getParam
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from couchpotato.core.settings.model import Notification as Notif
from sqlalchemy.sql.expression import or_
import time

log = CPLog(__name__)


class CoreNotifier(Notification):

    messages = []
    listen_to = [
        'movie.downloaded', 'movie.snatched',
        'updater.available', 'updater.updated',
    ]

    def __init__(self):
        super(CoreNotifier, self).__init__()

        addEvent('notify', self.notify)
        addEvent('notify.frontend', self.frontend)

        addApiView('notification.markread', self.markAsRead, docs = {
            'desc': 'Mark notifications as read',
            'params': {
                'id': {'desc': 'Notification id you want to mark as read.', 'type': 'int (comma separated)'},
            },
        })
        addApiView('notification.listener', self.listener)

        self.registerEvents()

    def registerEvents(self):

        # Library update, frontend refresh
        addEvent('library.update_finish', lambda data: fireEvent('notify.frontend', type = 'library.update', data = data))

    def markAsRead(self):
        ids = getParam('ids').split(',')

        db = get_session()

        q = db.query(Notif) \
            .filter(or_(*[Notif.id == tryInt(s) for s in ids]))
        q.update({Notif.read: True})

        db.commit()

        return jsonified({
            'success': True
        })

    def notify(self, message = '', data = {}):

        db = get_session()

        n = Notif(
            message = toUnicode(message),
            data = data
        )
        db.add(n)
        db.commit()

        ndict = n.to_dict()
        ndict['type'] = 'notification'
        ndict['time'] = time.time()
        self.messages.append(ndict)

        db.remove()

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

        # Get unread
        if getParam('init'):
            db = get_session()
            notifications = db.query(Notif).filter_by(read = False).all()
            for n in notifications:
                ndict = n.to_dict()
                ndict['type'] = 'notification'
                messages.append(ndict)

        self.messages = []
        return jsonified({
            'success': True,
            'result': messages,
        })

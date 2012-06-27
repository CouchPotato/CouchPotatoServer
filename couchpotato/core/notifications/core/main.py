from couchpotato import get_session
from couchpotato.api import addApiView, addNonBlockApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.request import jsonified, getParam
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from couchpotato.core.settings.model import Notification as Notif
from sqlalchemy.sql.expression import or_
import threading
import time
import uuid

log = CPLog(__name__)


class CoreNotifier(Notification):

    m_lock = threading.Lock()
    messages = []
    listeners = []

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
                'ids': {'desc': 'Notification id you want to mark as read. All if ids is empty.', 'type': 'int (comma separated)'},
            },
        })

        addApiView('notification.list', self.listView, docs = {
            'desc': 'Get list of notifications',
            'params': {
                'limit_offset': {'desc': 'Limit and offset the notification list. Examples: "50" or "50,30"'},
            },
            'return': {'type': 'object', 'example': """{
    'success': True,
    'empty': bool, any notification returned or not,
    'notifications': array, notifications found,
}"""}
        })

        addNonBlockApiView('notification.listener', (self.addListener, self.removeListener))
        addApiView('notification.listener', self.listener)

        addEvent('app.load', self.clean)

    def clean(self):

        db = get_session()
        db.query(Notif).filter(Notif.added <= (int(time.time()) - 2419200)).delete()
        db.commit()


    def markAsRead(self):

        ids = None
        if getParam('ids'):
            ids = [x.strip() for x in getParam('ids').split(',')]

        db = get_session()

        if ids:
            q = db.query(Notif).filter(or_(*[Notif.id == tryInt(s) for s in ids]))
        else:
            q = db.query(Notif).filter_by(read = False)

        q.update({Notif.read: True})

        db.commit()
        #db.close()

        return jsonified({
            'success': True
        })

    def listView(self):

        db = get_session()
        limit_offset = getParam('limit_offset', None)

        q = db.query(Notif)

        if limit_offset:
            splt = [x.strip() for x in limit_offset.split(',')]
            limit = splt[0]
            offset = 0 if len(splt) is 1 else splt[1]
            q = q.limit(limit).offset(offset)
        else:
            q = q.limit(200)

        results = q.all()
        notifications = []
        for n in results:
            ndict = n.to_dict()
            ndict['type'] = 'notification'
            notifications.append(ndict)

        #db.close()
        return jsonified({
            'success': True,
            'empty': len(notifications) == 0,
            'notifications': notifications
        })

    def notify(self, message = '', data = {}, listener = None):

        db = get_session()

        data['notification_type'] = listener if listener else 'unknown'

        n = Notif(
            message = toUnicode(message),
            data = data
        )
        db.add(n)
        db.commit()

        ndict = n.to_dict()
        ndict['type'] = 'notification'
        ndict['time'] = time.time()

        self.frontend(type = listener, data = data)

        #db.close()
        return True

    def frontend(self, type = 'notification', data = {}):

        self.m_lock.acquire()
        message = {
            'message_id': str(uuid.uuid4()),
            'time': time.time(),
            'type': type,
            'data': data,
        }
        self.messages.append(message)

        while len(self.listeners) > 0 and not self.shuttingDown():
            try:
                listener, last_id = self.listeners.pop()
                listener({
                    'success': True,
                    'result': [message],
                })
            except:
                break

        self.m_lock.release()
        self.cleanMessages()

    def addListener(self, callback, last_id = None):

        if last_id:
            messages = self.getMessages(last_id)
            if len(messages) > 0:
                return callback({
                    'success': True,
                    'result': messages,
                })

        self.listeners.append((callback, last_id))


    def removeListener(self, callback):

        for list_tuple in self.listeners:
            try:
                listener, last_id = list_tuple
                if listener == callback:
                    self.listeners.remove(list_tuple)
            except:
                pass

    def cleanMessages(self):
        self.m_lock.acquire()

        for message in self.messages:
            if message['time'] < (time.time() - 15):
                self.messages.remove(message)

        self.m_lock.release()

    def getMessages(self, last_id):
        self.m_lock.acquire()

        recent = []
        index = 0
        for i in xrange(len(self.messages)):
            index = len(self.messages) - i - 1
            if self.messages[index]["message_id"] == last_id: break
            recent = self.messages[index:]

        self.m_lock.release()

        return recent or []

    def listener(self):

        messages = []

        # Get unread
        if getParam('init'):
            db = get_session()

            notifications = db.query(Notif) \
                .filter(or_(Notif.read == False, Notif.added > (time.time() - 259200))) \
                .all()
            for n in notifications:
                ndict = n.to_dict()
                ndict['type'] = 'notification'
                messages.append(ndict)

        return jsonified({
            'success': True,
            'result': messages,
        })

from couchpotato import get_session
from couchpotato.api import addApiView, addNonBlockApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.request import jsonified, getParam
from couchpotato.core.helpers.variable import tryInt, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from couchpotato.core.settings.model import Notification as Notif
from couchpotato.environment import Env
from sqlalchemy.sql.expression import or_
import threading
import time
import uuid

log = CPLog(__name__)


class CoreNotifier(Notification):

    m_lock = threading.Lock()
    messages = []
    listeners = []

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

        fireEvent('schedule.interval', 'core.check_messages', self.checkMessages, hours = 12, single = True)

        addEvent('app.load', self.clean)
        addEvent('app.load', self.checkMessages)

    def clean(self):

        db = get_session()
        db.query(Notif).filter(Notif.added <= (int(time.time()) - 2419200)).delete()
        db.commit()


    def markAsRead(self):

        ids = None
        if getParam('ids'):
            ids = splitString(getParam('ids'))

        db = get_session()

        if ids:
            q = db.query(Notif).filter(or_(*[Notif.id == tryInt(s) for s in ids]))
        else:
            q = db.query(Notif).filter_by(read = False)

        q.update({Notif.read: True})

        db.commit()

        return jsonified({
            'success': True
        })

    def listView(self):

        db = get_session()
        limit_offset = getParam('limit_offset', None)

        q = db.query(Notif)

        if limit_offset:
            splt = splitString(limit_offset)
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

        return jsonified({
            'success': True,
            'empty': len(notifications) == 0,
            'notifications': notifications
        })

    def checkMessages(self):

        prop_name = 'messages.last_check'
        last_check = tryInt(Env.prop(prop_name, default = 0))

        messages = fireEvent('cp.messages', last_check = last_check, single = True)

        for message in messages:
            if message.get('time') > last_check:
                fireEvent('core.message', message = message.get('message'), data = message)

            if last_check < message.get('time'):
                last_check = message.get('time')

        Env.prop(prop_name, value = last_check)

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

        return True

    def frontend(self, type = 'notification', data = {}, message = None):

        self.m_lock.acquire()
        notification = {
            'message_id': str(uuid.uuid4()),
            'time': time.time(),
            'type': type,
            'data': data,
            'message': message,
        }
        self.messages.append(notification)

        while len(self.listeners) > 0 and not self.shuttingDown():
            try:
                listener, last_id = self.listeners.pop()
                listener({
                    'success': True,
                    'result': [notification],
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

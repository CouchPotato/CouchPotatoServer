from couchpotato import get_session
from couchpotato.api import addApiView, addNonBlockApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import tryInt, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from couchpotato.core.settings.model import Notification as Notif
from couchpotato.environment import Env
from operator import itemgetter
from sqlalchemy.sql.expression import or_
import threading
import time
import traceback
import uuid

log = CPLog(__name__)


class CoreNotifier(Notification):

    m_lock = None

    listen_to = [
        'renamer.after', 'movie.snatched',
        'updater.available', 'updater.updated',
        'core.message', 'core.message.important',
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

        fireEvent('schedule.interval', 'core.check_messages', self.checkMessages, hours = 12, single = True)
        fireEvent('schedule.interval', 'core.clean_messages', self.cleanMessages, seconds = 15, single = True)

        addEvent('app.load', self.clean)
        addEvent('app.load', self.checkMessages)

        self.messages = []
        self.listeners = []
        self.m_lock = threading.Lock()

    def clean(self):

        try:
            db = get_session()
            db.query(Notif).filter(Notif.added <= (int(time.time()) - 2419200)).delete()
            db.commit()
        except:
            log.error('Failed cleaning notification: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()

    def markAsRead(self, ids = None, **kwargs):

        ids = splitString(ids) if ids else None

        try:
            db = get_session()

            if ids:
                q = db.query(Notif).filter(or_(*[Notif.id == tryInt(s) for s in ids]))
            else:
                q = db.query(Notif).filter_by(read = False)

            q.update({Notif.read: True})
            db.commit()

            return {
                'success': True
            }
        except:
            log.error('Failed mark as read: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()

        return {
            'success': False
        }

    def listView(self, limit_offset = None, **kwargs):

        db = get_session()

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

        return {
            'success': True,
            'empty': len(notifications) == 0,
            'notifications': notifications
        }

    def checkMessages(self):

        prop_name = 'messages.last_check'
        last_check = tryInt(Env.prop(prop_name, default = 0))

        messages = fireEvent('cp.messages', last_check = last_check, single = True) or []

        for message in messages:
            if message.get('time') > last_check:
                message['sticky'] = True # Always sticky core messages

                message_type = 'core.message.important' if message.get('important') else 'core.message'
                fireEvent(message_type, message = message.get('message'), data = message)

            if last_check < message.get('time'):
                last_check = message.get('time')

        Env.prop(prop_name, value = last_check)

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        try:
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
        except:
            log.error('Failed notify: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()

    def frontend(self, type = 'notification', data = None, message = None):
        if not data: data = {}

        log.debug('Notifying frontend')

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
                log.debug('Failed sending to listener: %s', traceback.format_exc())

        self.listeners = []
        self.m_lock.release()

        log.debug('Done notifying frontend')

    def addListener(self, callback, last_id = None):

        if last_id:
            messages = self.getMessages(last_id)
            if len(messages) > 0:
                return callback({
                    'success': True,
                    'result': messages,
                })

        self.m_lock.acquire()
        self.listeners.append((callback, last_id))
        self.m_lock.release()


    def removeListener(self, callback):

        self.m_lock.acquire()
        new_listeners = []
        for list_tuple in self.listeners:
            try:
                listener, last_id = list_tuple
                if listener != callback:
                    new_listeners.append(list_tuple)
            except:
                log.debug('Failed removing listener: %s', traceback.format_exc())

        self.listeners = new_listeners
        self.m_lock.release()

    def cleanMessages(self):

        if len(self.messages) == 0:
            return

        log.debug('Cleaning messages')
        self.m_lock.acquire()

        time_ago = (time.time() - 15)
        self.messages[:] = [m for m in self.messages if (m['time'] > time_ago)]

        self.m_lock.release()
        log.debug('Done cleaning messages')

    def getMessages(self, last_id):

        log.debug('Getting messages with id: %s', last_id)
        self.m_lock.acquire()

        recent = []
        try:
            index = map(itemgetter('message_id'), self.messages).index(last_id)
            recent = self.messages[index + 1:]
        except:
            pass

        self.m_lock.release()
        log.debug('Returning for %s %s messages', (last_id, len(recent)))

        return recent

    def listener(self, init = False, **kwargs):

        messages = []

        # Get unread
        if init:
            db = get_session()

            notifications = db.query(Notif) \
                .filter(or_(Notif.read == False, Notif.added > (time.time() - 259200))) \
                .all()

            for n in notifications:
                ndict = n.to_dict()
                ndict['type'] = 'notification'
                messages.append(ndict)

        return {
            'success': True,
            'result': messages,
        }

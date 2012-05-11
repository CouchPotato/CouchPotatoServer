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
                'ids': {'desc': 'Notification id you want to mark as read.', 'type': 'int (comma separated)'},
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

        addApiView('notification.listener', self.listener)

        self.registerEvents()

    def registerEvents(self):

        # Library update, frontend refresh
        addEvent('library.update_finish', lambda data: fireEvent('notify.frontend', type = 'library.update', data = data))

    def markAsRead(self):
        ids = [x.strip() for x in getParam('ids').split(',')]

        db = get_session()

        q = db.query(Notif) \
            .filter(or_(*[Notif.id == tryInt(s) for s in ids]))
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
        self.messages.append(ndict)

        #db.close()
        return True

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

            notifications = db.query(Notif) \
                .filter(or_(Notif.read == False, Notif.added > (time.time() - 259200))) \
                .all()
            for n in notifications:
                ndict = n.to_dict()
                ndict['type'] = 'notification'
                messages.append(ndict)

            #db.close()

        self.messages = []
        return jsonified({
            'success': True,
            'result': messages,
        })

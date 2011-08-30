from couchpotato import get_session
from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from couchpotato.core.settings.model import History as Hist
import time

log = CPLog(__name__)


class History(Notification):

    listen_to = ['movie.downloaded', 'movie.snatched', 'renamer.canceled']

    def __init__(self):

        addEvent('notify', self.notify)

        addEvent('app.load', self.test)


    def notify(self, message = '', data = {}):

        db = get_session()
        history = Hist(
            added = int(time.time()),
            message = message,
            type = type,
            release_id = data.get('id', 0)
        )
        db.add(history)
        db.commit()

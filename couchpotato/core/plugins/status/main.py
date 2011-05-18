from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Status

log = CPLog(__name__)


class StatusPlugin(Plugin):

    statuses = {
        'needs_update': 'Needs update',
        'active': 'Active',
        'done': 'Done',
        'downloaded': 'Downloaded',
        'wanted': 'Wanted',
        'snatched': 'Snatched',
        'deleted': 'Deleted',
    }

    def __init__(self):
        addEvent('status.add', self.add)
        addEvent('status.get', self.add) # Alias for .add
        addEvent('status.all', self.all)
        addEvent('app.load', self.fill)

        path = self.registerStatic(__file__)
        fireEvent('register_script', path + 'status.js')

    def all(self):

        db = get_session()

        statuses = db.query(Status).all()

        temp = []
        for status in statuses:
            s = status.to_dict()
            temp.append(s)

        return temp

    def add(self, identifier):

        db = get_session()

        s = db.query(Status).filter_by(identifier = identifier).first()
        if not s:
            s = Status(
                identifier = identifier,
                label = identifier.capitalize()
            )
            db.add(s)
            db.commit()

        status_dict = s.to_dict()

        return status_dict

    def fill(self):

        db = get_session()

        for identifier, label in self.statuses.iteritems():
            s = db.query(Status).filter_by(identifier = identifier).first()
            if not s:
                log.info('Creating status: %s' % label)
                s = Status(
                    identifier = identifier,
                    label = toUnicode(label)
                )
                db.add(s)

            s.label = label
            db.commit()


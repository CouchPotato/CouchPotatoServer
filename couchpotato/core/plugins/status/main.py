from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.request import jsonified
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
        'ignored': 'Ignored',
    }

    def __init__(self):
        addEvent('status.add', self.add)
        addEvent('status.get', self.add) # Alias for .add
        addEvent('status.get_by_id', self.getById)
        addEvent('status.all', self.all)
        addEvent('app.initialize', self.fill)

        addApiView('status.list', self.list, docs = {
            'desc': 'Check for available update',
            'return': {'type': 'object', 'example': """{
            'success': True,
            'list': array, statuses
}"""}
        })

    def list(self):

        return jsonified({
            'success': True,
            'list': self.all()
        })

    def getById(self, id):
        db = get_session()
        status = db.query(Status).filter_by(id = id).first()
        status_dict = status.to_dict()
        #db.close()

        return status_dict

    def all(self):

        db = get_session()

        statuses = db.query(Status).all()

        temp = []
        for status in statuses:
            s = status.to_dict()
            temp.append(s)

        #db.close()
        return temp

    def add(self, identifier):

        db = get_session()

        s = db.query(Status).filter_by(identifier = identifier).first()
        if not s:
            s = Status(
                identifier = identifier,
                label = toUnicode(identifier.capitalize())
            )
            db.add(s)
            db.commit()

        status_dict = s.to_dict()

        #db.close()
        return status_dict

    def fill(self):

        db = get_session()

        for identifier, label in self.statuses.iteritems():
            s = db.query(Status).filter_by(identifier = identifier).first()
            if not s:
                log.info('Creating status: %s', label)
                s = Status(
                    identifier = identifier,
                    label = toUnicode(label)
                )
                db.add(s)

            s.label = toUnicode(label)
            db.commit()

        #db.close()


import traceback
from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
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
        'failed': 'Failed',
        'deleted': 'Deleted',
        'ignored': 'Ignored',
        'available': 'Available',
        'suggest': 'Suggest',
        'seeding': 'Seeding',
        'missing': 'Missing',
    }
    status_cached = {}

    def __init__(self):
        addEvent('status.get', self.get)
        addEvent('status.get_by_id', self.getById)
        addEvent('status.all', self.all)
        addEvent('app.initialize', self.fill)
        addEvent('app.load', self.all)  # Cache all statuses

        addApiView('status.list', self.list, docs = {
            'desc': 'Check for available update',
            'return': {'type': 'object', 'example': """{
            'success': True,
            'list': array, statuses
}"""}
        })

    def list(self, **kwargs):

        return {
            'success': True,
            'list': self.all()
        }

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

            # Update cache
            self.status_cached[status.identifier] = s

        return temp

    def get(self, identifiers):

        if not isinstance(identifiers, list):
            identifiers = [identifiers]

        try:
            db = get_session()
            return_list = []

            for identifier in identifiers:

                if self.status_cached.get(identifier):
                    return_list.append(self.status_cached.get(identifier))
                    continue

                s = db.query(Status).filter_by(identifier = identifier).first()
                if not s:
                    s = Status(
                        identifier = identifier,
                        label = toUnicode(identifier.capitalize())
                    )
                    db.add(s)
                    db.commit()

                status_dict = s.to_dict()

                self.status_cached[identifier] = status_dict
                return_list.append(status_dict)

            return return_list if len(identifiers) > 1 else return_list[0]
        except:
            log.error('Failed: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()

    def fill(self):

        try:
            db = get_session()

            for identifier, label in self.statuses.items():
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
        except:
            log.error('Failed: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()


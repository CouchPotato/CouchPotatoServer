from couchpotato import get_session
from couchpotato.core.event import addEvent
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Library


class LibraryPlugin(Plugin):

    def __init__(self):
        addEvent('library.add', self.add)

    def add(self, attrs = {}):

        db = get_session();

        l = db.query(Library).filter_by(identifier = attrs.get('identifier')).first()

        if not l:
            l = Library(
                name = attrs.get('name'),
                year = attrs.get('year'),
                identifier = attrs.get('identifier'),
                description = attrs.get('description')
            )
            db.add(l)
            db.commit()

        return l

    def update(self, item):

        pass

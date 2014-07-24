from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.library.base import LibraryBase

log = CPLog(__name__)


class Library(LibraryBase):
    def __init__(self):
        addEvent('library.title', self.title)
        addEvent('library.related', self.related)
        addEvent('library.root', self.root)

        addApiView('library.query', self.queryView)
        addApiView('library.related', self.relatedView)

    def queryView(self, media_id, **kwargs):
        db = get_db()
        media = db.get('id', media_id)

        return {
            'result': fireEvent('library.query', media, single = True)
        }

    def relatedView(self, media_id, **kwargs):
        db = get_db()
        media = db.get('id', media_id)

        return {
            'result': fireEvent('library.related', media, single = True)
        }

    def title(self, library):
        return fireEvent(
            'library.query',
            library,

            condense = False,
            include_year = False,
            include_identifier = False,
            single = True
        )

    def related(self, media):
        result = {media['type']: media}

        db = get_db()
        cur = media

        while cur and cur.get('parent_id'):
            cur = db.get('id', cur['parent_id'])

            result[cur['type']] = cur

        return result

    def root(self, media):
        db = get_db()
        cur = media

        while cur and cur.get('parent_id'):
            cur = db.get('id', cur['parent_id'])

        return cur

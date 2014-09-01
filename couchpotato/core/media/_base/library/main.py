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
        addEvent('library.tree', self.tree)

        addEvent('library.root', self.root)

        addApiView('library.query', self.queryView)
        addApiView('library.related', self.relatedView)
        addApiView('library.tree', self.treeView)

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

    def treeView(self, media_id, **kwargs):
        db = get_db()
        media = db.get('id', media_id)

        return {
            'result': fireEvent('library.tree', media, single = True)
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
        result = {self.key(media['type']): media}

        db = get_db()
        cur = media

        while cur and cur.get('parent_id'):
            cur = db.get('id', cur['parent_id'])

            result[self.key(cur['type'])] = cur

        children = db.get_many('media_children', media['_id'], with_doc = True)

        for item in children:
            key = self.key(item['doc']['type']) + 's'

            if key not in result:
                result[key] = []

            result[key].append(item['doc'])

        return result

    def root(self, media):
        db = get_db()
        cur = media

        while cur and cur.get('parent_id'):
            cur = db.get('id', cur['parent_id'])

        return cur

    def tree(self, media = None, media_id = None):
        db = get_db()

        if media:
            result = media
        elif media_id:
            result = db.get('id', media_id, with_doc = True)
        else:
            return None

        # Find children
        items = db.get_many('media_children', result['_id'], with_doc = True)
        keys = []

        # Build children arrays
        for item in items:
            key = self.key(item['doc']['type']) + 's'

            if key not in result:
                result[key] = {}
            elif type(result[key]) is not dict:
                result[key] = {}

            if key not in keys:
                keys.append(key)

            result[key][item['_id']] = fireEvent('library.tree', item['doc'], single = True)

        # Unique children
        for key in keys:
            result[key] = result[key].values()

        # Include releases
        result['releases'] = fireEvent('release.for_media', result['_id'], single = True)

        return result

    def key(self, media_type):
        parts = media_type.split('.')
        return parts[-1]

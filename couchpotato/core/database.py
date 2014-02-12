import json
import time
import traceback
from couchpotato import CPLog
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent

log = CPLog(__name__)


class Database(object):

    indexes = []
    db = None

    def __init__(self):

        addApiView('database.list_documents', self.listDocuments)
        addApiView('database.document.update', self.updateDocument)
        addApiView('database.document.delete', self.deleteDocument)

        addEvent('database.setup_index', self.setupIndex)

    def getDB(self):

        if not self.db:
            from couchpotato import get_db
            self.db = get_db()

        return self.db

    def setupIndex(self, index_name, klass):

        self.indexes.append(index_name)

        db = self.getDB()

        # Category index
        try:
            db.add_index(klass(db.path, index_name))
            db.reindex_index(index_name)
        except:
            previous_version = db.indexes_names[index_name]._version
            current_version = klass._version

            # Only edit index if versions are different
            if previous_version < current_version:
                log.debug('Index "%s" already exists, updating and reindexing', index_name)
                db.edit_index(klass(db.path, index_name), reindex = True)

    def deleteDocument(self, **kwargs):

        db = self.getDB()

        try:

            document_id = kwargs.get('_request').get_argument('id')
            document = db.get('id', document_id)
            db.delete(document)

            return {
                'success': True
            }
        except:
            return {
                'success': False,
                'error': traceback.format_exc()
            }

    def updateDocument(self, **kwargs):

        db = self.getDB()

        try:

            document = json.loads(kwargs.get('_request').get_argument('document'))
            d = db.update(document)
            document.update(d)

            return {
                'success': True,
                'document': document
            }
        except:
            return {
                'success': False,
                'error': traceback.format_exc()
            }

    def listDocuments(self, **kwargs):
        db = self.getDB()

        results = {
            'unknown': []
        }

        for document in db.all('id'):
            key = document.get('_t', 'unknown')

            if kwargs.get('show') and key != kwargs.get('show'):
                continue

            if not results.get(key):
                results[key] = []
            results[key].append(document)


        return results

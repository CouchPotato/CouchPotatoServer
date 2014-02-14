import json
import os
import time
import traceback
from couchpotato import CPLog
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode

log = CPLog(__name__)


class Database(object):

    indexes = []
    db = None

    def __init__(self):

        addApiView('database.list_documents', self.listDocuments)
        addApiView('database.document.update', self.updateDocument)
        addApiView('database.document.delete', self.deleteDocument)

        addEvent('database.setup_index', self.setupIndex)
        addEvent('app.migrate', self.migrate)

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

    def migrate(self):
        time.sleep(1)

        from couchpotato import Env
        old_db = os.path.join(Env.get('data_dir'), 'couchpotato.db')

        if os.path.isfile(old_db):

            import sqlite3
            conn = sqlite3.connect(old_db)

            c = conn.cursor()

            migrate_list = {
                'category': ['id', 'label', 'order', 'required', 'preferred', 'ignored', 'destination'],
                'profile': ['id', 'label', 'order', 'core', 'hide'],
                'profiletype': ['id', 'order', 'finish', 'wait_for', 'quality_id', 'profile_id'],
                'quality': ['id', 'identifier', 'order', 'size_min', 'size_max'],
                'movie': ['id', 'last_edit', 'library_id', 'status_id', 'profile_id', 'category_id'],
                'library': ['id', 'identifier'],
                'release': ['id', 'identifier', 'movie_id', 'status_id', 'quality_id', 'last_edit'],
                'status': ['id', 'identifier'],
                'properties': ['id', 'identifier', 'value'],
            }

            migrate_data = {}

            for ml in migrate_list:
                migrate_data[ml] = {}
                rows = migrate_list[ml]
                c.execute('SELECT %s FROM `%s`' % ('`' + '`,`'.join(rows) + '`', ml))
                for p in c.fetchall():
                    columns = {}
                    for row in migrate_list[ml]:
                        columns[row] = p[rows.index(row)]
                    migrate_data[ml][p[0]] = columns

            db = self.getDB()

            # Categories
            categories = migrate_data['category']
            category_link = {}
            for x in categories:
                continue

                c = categories[x]
                new_c = db.insert({
                    '_t': 'category',
                    'order': c.get('order', 999),
                    'label': toUnicode(c.get('label', '')),
                    'ignored': toUnicode(c.get('ignored', '')),
                    'preferred': toUnicode(c.get('preferred', '')),
                    'required': toUnicode(c.get('required', '')),
                    'destination': toUnicode(c.get('destination', '')),
                })

                category_link[x] = new_c.get('_id')

            # Profiles
            new_profiles = db.all('profile', with_doc = True)
            new_profiles_by_label = {}
            for x in new_profiles:

                # Remove default non core profiles
                if not x['doc'].get('core'):
                    db.delete(x['doc'])
                else:
                    new_profiles_by_label[x['doc']['label']] = x['_id']

            profiles = migrate_data['profile']
            profile_link = {}
            for x in profiles:
                p = profiles[x]

                exists = new_profiles_by_label.get(p.get('label'))

                # Update existing with order only
                if exists and p.get('core'):
                    profile = db.get('id', exists)
                    profile['order'] = p.get('order')
                    db.update(profile)

                    profile_link[x] = profile.get('_id')
                else:

                    new_profile = {
                        '_t': 'profile',
                        'label': p.get('label'),
                        'order': int(p.get('order', 999)),
                        'core': p.get('core', False),
                        'qualities': [],
                        'wait_for': [],
                        'finish': []
                    }

                    types = migrate_data['profiletype']
                    for profile_type in types:
                        p_type = types[profile_type]
                        if types[profile_type]['profile_id'] == p['id']:
                            new_profile['finish'].append(p_type['finish'])
                            new_profile['wait_for'].append(p_type['wait_for'])
                            new_profile['qualities'].append(migrate_data['quality'][p_type['quality_id']]['identifier'])
                    print new_profile

                    new_profile.update(db.insert(new_profile))

                    profile_link[x] = new_profile.get('_id')

import json
import os
import time
import traceback

from couchpotato import CPLog
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getImdb, tryInt


log = CPLog(__name__)


class Database(object):

    indexes = []
    db = None

    def __init__(self):

        addApiView('database.list_documents', self.listDocuments)
        addApiView('database.reindex', self.reindex)
        addApiView('database.compact', self.compact)
        addApiView('database.document.update', self.updateDocument)
        addApiView('database.document.delete', self.deleteDocument)

        addEvent('database.setup_index', self.setupIndex)
        addEvent('app.migrate', self.migrate)
        addEvent('app.after_shutdown', self.close)

    def getDB(self):

        if not self.db:
            from couchpotato import get_db
            self.db = get_db()

        return self.db

    def close(self, **kwargs):
        self.getDB().close()

    def setupIndex(self, index_name, klass):

        self.indexes.append(index_name)

        db = self.getDB()

        # Category index
        index_instance = klass(db.path, index_name)
        try:
            db.add_index(index_instance)
            db.reindex_index(index_name)
        except:
            previous = db.indexes_names[index_name]
            previous_version = previous._version
            current_version = klass._version

            # Only edit index if versions are different
            if previous_version < current_version:
                log.debug('Index "%s" already exists, updating and reindexing', index_name)
                db.destroy_index(previous)
                db.add_index(index_instance)
                db.reindex_index(index_name)

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

    def reindex(self, **kwargs):

        success = True
        try:
            db = self.getDB()
            db.reindex()
        except:
            log.error('Failed index: %s', traceback.format_exc())
            success = False

        return {
            'success': success
        }

    def compact(self, **kwargs):

        success = True
        try:
            db = self.getDB()
            db.compact()
        except:
            log.error('Failed compact: %s', traceback.format_exc())
            success = False

        return {
            'success': success
        }

    def migrate(self):

        from couchpotato import Env
        old_db = os.path.join(Env.get('data_dir'), 'couchpotato.db')
        if not os.path.isfile(old_db): return

        log.info('=' * 30)
        log.info('Migrating database, hold on..')
        time.sleep(1)

        if os.path.isfile(old_db):

            migrate_start = time.time()

            import sqlite3
            conn = sqlite3.connect(old_db)

            migrate_list = {
                'category': ['id', 'label', 'order', 'required', 'preferred', 'ignored', 'destination'],
                'profile': ['id', 'label', 'order', 'core', 'hide'],
                'profiletype': ['id', 'order', 'finish', 'wait_for', 'quality_id', 'profile_id'],
                'quality': ['id', 'identifier', 'order', 'size_min', 'size_max'],
                'movie': ['id', 'last_edit', 'library_id', 'status_id', 'profile_id', 'category_id'],
                'library': ['id', 'identifier', 'info'],
                'librarytitle': ['id', 'title', 'default', 'libraries_id'],
                'library_files__file_library': ['library_id', 'file_id'],
                'release': ['id', 'identifier', 'movie_id', 'status_id', 'quality_id', 'last_edit'],
                'releaseinfo': ['id', 'identifier', 'value', 'release_id'],
                'release_files__file_release': ['release_id', 'file_id'],
                'status': ['id', 'identifier'],
                'properties': ['id', 'identifier', 'value'],
                'file': ['id', 'path', 'type_id'],
                'filetype': ['identifier', 'id']
            }

            migrate_data = {}

            c = conn.cursor()

            for ml in migrate_list:
                migrate_data[ml] = {}
                rows = migrate_list[ml]

                try:
                    c.execute('SELECT %s FROM `%s`' % ('`' + '`,`'.join(rows) + '`', ml))
                except:
                    # ignore faulty destination_id database
                    if ml == 'category':
                        migrate_data[ml] = {}
                    else:
                        raise

                for p in c.fetchall():
                    columns = {}
                    for row in migrate_list[ml]:
                        columns[row] = p[rows.index(row)]

                    if not migrate_data[ml].get(p[0]):
                        migrate_data[ml][p[0]] = columns
                    else:
                        if not isinstance(migrate_data[ml][p[0]], list):
                            migrate_data[ml][p[0]] = [migrate_data[ml][p[0]]]
                        migrate_data[ml][p[0]].append(columns)

            conn.close()

            log.info('Getting data took %s', time.time() - migrate_start)

            db = self.getDB()

            # Use properties
            properties = migrate_data['properties']
            log.info('Importing %s properties', len(properties))
            for x in properties:
                property = properties[x]
                Env.prop(property.get('identifier'), property.get('value'))

            # Categories
            categories = migrate_data.get('category', [])
            log.info('Importing %s categories', len(categories))
            category_link = {}
            for x in categories:
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
            log.info('Importing profiles')
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
                    profile['order'] = tryInt(p.get('order'))
                    profile['hide'] = p.get('hide') in [1, True, 'true', 'True']
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

                    new_profile.update(db.insert(new_profile))

                    profile_link[x] = new_profile.get('_id')

            # Qualities
            log.info('Importing quality sizes')
            new_qualities = db.all('quality', with_doc = True)
            new_qualities_by_identifier = {}
            for x in new_qualities:
                new_qualities_by_identifier[x['doc']['identifier']] = x['_id']

            qualities = migrate_data['quality']
            quality_link = {}
            for x in qualities:
                q = qualities[x]
                q_id = new_qualities_by_identifier[q.get('identifier')]

                quality = db.get('id', q_id)
                quality['order'] = q.get('order')
                quality['size_min'] = tryInt(q.get('size_min'))
                quality['size_max'] = tryInt(q.get('size_max'))
                db.update(quality)

                quality_link[x] = quality

            # Titles
            titles = migrate_data['librarytitle']
            titles_by_library = {}
            for x in titles:
                title = titles[x]
                if title.get('default'):
                    titles_by_library[title.get('libraries_id')] = title.get('title')

            # Releases
            releaseinfos = migrate_data['releaseinfo']
            for x in releaseinfos:
                info = releaseinfos[x]

                # Skip if release doesn't exist for this info
                if not migrate_data['release'].get(info.get('release_id')):
                    continue

                if not migrate_data['release'][info.get('release_id')].get('info'):
                    migrate_data['release'][info.get('release_id')]['info'] = {}

                migrate_data['release'][info.get('release_id')]['info'][info.get('identifier')] = info.get('value')

            releases = migrate_data['release']
            releases_by_media = {}
            for x in releases:
                release = releases[x]
                if not releases_by_media.get(release.get('movie_id')):
                    releases_by_media[release.get('movie_id')] = []

                releases_by_media[release.get('movie_id')].append(release)

            # Type ids
            types = migrate_data['filetype']
            type_by_id = {}
            for t in types:
                type = types[t]
                type_by_id[type.get('id')] = type

            # Media
            log.info('Importing %s media items', len(migrate_data['movie']))
            statuses = migrate_data['status']
            libraries = migrate_data['library']
            library_files = migrate_data['library_files__file_library']
            releases_files = migrate_data['release_files__file_release']
            all_files = migrate_data['file']
            poster_type = migrate_data['filetype']['poster']
            medias = migrate_data['movie']
            for x in medias:
                m = medias[x]

                status = statuses.get(m['status_id']).get('identifier')
                l = libraries[m['library_id']]

                # Only migrate wanted movies, Skip if no identifier present
                if not getImdb(l.get('identifier')): continue

                profile_id = profile_link.get(m['profile_id'])
                category_id = category_link.get(m['category_id'])
                title = titles_by_library.get(m['library_id'])
                releases = releases_by_media.get(x, [])
                info = json.loads(l.get('info', ''))

                files = library_files.get(m['library_id'], [])
                if not isinstance(files, list):
                    files = [files]

                added_media = fireEvent('movie.add', {
                    'info': info,
                    'identifier': l.get('identifier'),
                    'profile_id': profile_id,
                    'category_id': category_id,
                    'title': title
                }, force_readd = False, search_after = False, update_after = False, notify_after = False, status = status, single = True)

                if not added_media:
                    log.error('Failed adding media %s: %s', (l.get('identifier'), info))
                    continue

                added_media['files'] = added_media.get('files', {})
                for f in files:
                    ffile = all_files[f.get('file_id')]

                    # Only migrate posters
                    if ffile.get('type_id') == poster_type.get('id'):
                        if ffile.get('path') not in added_media['files'].get('image_poster', []) and os.path.isfile(ffile.get('path')):
                            added_media['files']['image_poster'] = [ffile.get('path')]
                            break

                if 'image_poster' in added_media['files']:
                    db.update(added_media)

                for rel in releases:

                    empty_info = False
                    if not rel.get('info'):
                        empty_info = True
                        rel['info'] = {}

                    quality = quality_link.get(rel.get('quality_id'))
                    if not quality:
                        continue

                    release_status = statuses.get(rel.get('status_id')).get('identifier')

                    if rel['info'].get('download_id'):
                        status_support = rel['info'].get('download_status_support', False) in [True, 'true', 'True']
                        rel['info']['download_info'] = {
                            'id': rel['info'].get('download_id'),
                            'downloader': rel['info'].get('download_downloader'),
                            'status_support': status_support,
                        }

                    # Add status to keys
                    rel['info']['status'] = release_status
                    if not empty_info:
                        fireEvent('release.create_from_search', [rel['info']], added_media, quality, single = True)
                    else:
                        release = {
                            '_t': 'release',
                            'identifier': rel.get('identifier'),
                            'media_id': added_media.get('_id'),
                            'quality': quality.get('identifier'),
                            'status': release_status,
                            'last_edit': int(time.time()),
                            'files': {}
                        }

                        # Add downloader info if provided
                        try:
                            release['download_info'] = rel['info']['download_info']
                            del rel['download_info']
                        except:
                            pass

                        # Add files
                        release_files = releases_files.get(rel.get('id'), [])
                        if not isinstance(release_files, list):
                            release_files = [release_files]

                        if len(release_files) == 0:
                            continue

                        for f in release_files:
                            rfile = all_files[f.get('file_id')]
                            file_type = type_by_id.get(rfile.get('type_id')).get('identifier')

                            if not release['files'].get(file_type):
                                release['files'][file_type] = []

                            release['files'][file_type].append(rfile.get('path'))

                        try:
                            rls = db.get('release_identifier', rel.get('identifier'), with_doc = True)['doc']
                            rls.update(release)
                            db.update(rls)
                        except:
                            db.insert(release)

            log.info('Total migration took %s', time.time() - migrate_start)
            log.info('=' * 30)

            # rename old database
            log.info('Renaming old database to %s ', old_db + '.old')
            os.rename(old_db, old_db + '.old')

            if os.path.isfile(old_db + '-wal'):
                os.rename(old_db + '-wal', old_db + '-wal.old')
            if os.path.isfile(old_db + '-shm'):
                os.rename(old_db + '-shm', old_db + '-shm.old')

import json
import os
import time
import traceback
from sqlite3 import OperationalError

from CodernityDB.database import RecordNotFound
from CodernityDB.index import IndexException, IndexNotFoundException, IndexConflict
from couchpotato import CPLog
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.helpers.encoding import toUnicode, sp
from couchpotato.core.helpers.variable import getImdb, tryInt, randomString


log = CPLog(__name__)


class Database(object):

    indexes = None
    db = None

    def __init__(self):

        self.indexes = {}

        addApiView('database.list_documents', self.listDocuments)
        addApiView('database.reindex', self.reindex)
        addApiView('database.compact', self.compact)
        addApiView('database.document.update', self.updateDocument)
        addApiView('database.document.delete', self.deleteDocument)

        addEvent('database.setup.after', self.startup_compact)
        addEvent('database.setup_index', self.setupIndex)
        addEvent('database.delete_corrupted', self.deleteCorrupted)

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

        self.indexes[index_name] = klass

        db = self.getDB()

        # Category index
        index_instance = klass(db.path, index_name)
        try:

            # Make sure store and bucket don't exist
            exists = []
            for x in ['buck', 'stor']:
                full_path = os.path.join(db.path, '%s_%s' % (index_name, x))
                if os.path.exists(full_path):
                    exists.append(full_path)

            if index_name not in db.indexes_names:

                # Remove existing buckets if index isn't there
                for x in exists:
                    os.unlink(x)

                # Add index (will restore buckets)
                db.add_index(index_instance)
                db.reindex_index(index_name)
            else:
                # Previous info
                previous = db.indexes_names[index_name]
                previous_version = previous._version
                current_version = klass._version

                # Only edit index if versions are different
                if previous_version < current_version:
                    log.debug('Index "%s" already exists, updating and reindexing', index_name)
                    db.destroy_index(previous)
                    db.add_index(index_instance)
                    db.reindex_index(index_name)

        except:
            log.error('Failed adding index %s: %s', (index_name, traceback.format_exc()))

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

    def deleteCorrupted(self, _id, traceback_error = ''):

        db = self.getDB()

        try:
            log.debug('Deleted corrupted document "%s": %s', (_id, traceback_error))
            corrupted = db.get('id', _id, with_storage = False)
            db._delete_id_index(corrupted.get('_id'), corrupted.get('_rev'), None)
        except:
            log.debug('Failed deleting corrupted: %s', traceback.format_exc())

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

    def compact(self, try_repair = True, **kwargs):

        success = False
        db = self.getDB()

        # Removing left over compact files
        db_path = sp(db.path)
        for f in os.listdir(sp(db.path)):
            for x in ['_compact_buck', '_compact_stor']:
                if f[-len(x):] == x:
                    os.unlink(os.path.join(db_path, f))

        try:
            start = time.time()
            size = float(db.get_db_details().get('size', 0))
            log.debug('Compacting database, current size: %sMB', round(size/1048576, 2))

            db.compact()
            new_size = float(db.get_db_details().get('size', 0))
            log.debug('Done compacting database in %ss, new size: %sMB, saved: %sMB', (round(time.time()-start, 2), round(new_size/1048576, 2), round((size-new_size)/1048576, 2)))
            success = True
        except (IndexException, AttributeError):
            if try_repair:
                log.error('Something wrong with indexes, trying repair')

                # Remove all indexes
                old_indexes = self.indexes.keys()
                for index_name in old_indexes:
                    try:
                        db.destroy_index(index_name)
                    except IndexNotFoundException:
                        pass
                    except:
                        log.error('Failed removing old index %s', index_name)

                # Add them again
                for index_name in self.indexes:
                    klass = self.indexes[index_name]

                    # Category index
                    index_instance = klass(db.path, index_name)
                    try:
                        db.add_index(index_instance)
                        db.reindex_index(index_name)
                    except IndexConflict:
                        pass
                    except:
                        log.error('Failed adding index %s', index_name)
                        raise

                self.compact(try_repair = False)
            else:
                log.error('Failed compact: %s', traceback.format_exc())

        except:
            log.error('Failed compact: %s', traceback.format_exc())

        return {
            'success': success
        }

    # Compact on start
    def startup_compact(self):
        from couchpotato import Env

        db = self.getDB()

        # Try fix for migration failures on desktop
        if Env.get('desktop'):
            try:
                list(db.all('profile', with_doc = True))
            except RecordNotFound:

                failed_location = '%s_failed' % db.path
                old_db = os.path.join(Env.get('data_dir'), 'couchpotato.db.old')

                if not os.path.isdir(failed_location) and os.path.isfile(old_db):
                    log.error('Corrupt database, trying migrate again')
                    db.close()

                    # Rename database folder
                    os.rename(db.path, '%s_failed' % db.path)

                    # Rename .old database to try another migrate
                    os.rename(old_db, old_db[:-4])

                    fireEventAsync('app.restart')
                else:
                    log.error('Migration failed and couldn\'t recover database. Please report on GitHub, with this message.')
                    db.reindex()

                return

        # Check size and compact if needed
        size = db.get_db_details().get('size')
        prop_name = 'last_db_compact'
        last_check = int(Env.prop(prop_name, default = 0))

        if last_check < time.time()-604800: # 7 days
            self.compact()
            Env.prop(prop_name, value = int(time.time()))

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
            rename_old = False

            try:

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
                            rename_old = True
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
                if not db.opened:
                    return

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
                                if p_type['quality_id']:
                                    new_profile['finish'].append(p_type['finish'])
                                    new_profile['wait_for'].append(p_type['wait_for'])
                                    new_profile['qualities'].append(migrate_data['quality'][p_type['quality_id']]['identifier'])

                        if len(new_profile['qualities']) > 0:
                            new_profile.update(db.insert(new_profile))
                            profile_link[x] = new_profile.get('_id')
                        else:
                            log.error('Corrupt profile list for "%s", using default.', p.get('label'))

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
                    l = libraries.get(m['library_id'])

                    # Only migrate wanted movies, Skip if no identifier present
                    if not l or not getImdb(l.get('identifier')): continue

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
                                rfile = all_files.get(f.get('file_id'))
                                if not rfile:
                                    continue

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

                rename_old = True

            except OperationalError:
                log.error('Migrating from faulty database, probably a (too) old version: %s', traceback.format_exc())
                
                rename_old = True
            except:
                log.error('Migration failed: %s', traceback.format_exc())


            # rename old database
            if rename_old:
                random = randomString()
                log.info('Renaming old database to %s ', '%s.%s_old' % (old_db, random))
                os.rename(old_db, '%s.%s_old' % (old_db, random))

                if os.path.isfile(old_db + '-wal'):
                    os.rename(old_db + '-wal', '%s-wal.%s_old' % (old_db, random))
                if os.path.isfile(old_db + '-shm'):
                    os.rename(old_db + '-shm', '%s-shm.%s_old' % (old_db, random))

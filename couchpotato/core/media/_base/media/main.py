from datetime import timedelta
import time
import traceback
from string import ascii_lowercase

from CodernityDB.database import RecordNotFound, RecordDeleted
from couchpotato import tryInt, get_db
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import splitString, getImdb, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.media import MediaBase
from .index import MediaIndex, MediaStatusIndex, MediaTypeIndex, TitleSearchIndex, TitleIndex, StartsWithIndex, MediaChildrenIndex, MediaTagIndex


log = CPLog(__name__)


class MediaPlugin(MediaBase):

    _database = {
        'media': MediaIndex,
        'media_search_title': TitleSearchIndex,
        'media_status': MediaStatusIndex,
        'media_tag': MediaTagIndex,
        'media_by_type': MediaTypeIndex,
        'media_title': TitleIndex,
        'media_startswith': StartsWithIndex,
        'media_children': MediaChildrenIndex,
    }

    def __init__(self):

        addApiView('media.refresh', self.refresh, docs = {
            'desc': 'Refresh a any media type by ID',
            'params': {
                'id': {'desc': 'Movie, Show, Season or Episode ID(s) you want to refresh.', 'type': 'int (comma separated)'},
            }
        })

        addApiView('media.list', self.listView, docs = {
            'desc': 'List media',
            'params': {
                'type': {'type': 'string', 'desc': 'Media type to filter on.'},
                'status': {'type': 'array or csv', 'desc': 'Filter media by status. Example:"active,done"'},
                'release_status': {'type': 'array or csv', 'desc': 'Filter media by status of its releases. Example:"snatched,available"'},
                'limit_offset': {'desc': 'Limit and offset the media list. Examples: "50" or "50,30"'},
                'starts_with': {'desc': 'Starts with these characters. Example: "a" returns all media starting with the letter "a"'},
                'search': {'desc': 'Search media title'},
            },
            'return': {'type': 'object', 'example': """{
    'success': True,
    'empty': bool, any media returned or not,
    'media': array, media found,
}"""}
        })

        addApiView('media.get', self.getView, docs = {
            'desc': 'Get media by id',
            'params': {
                'id': {'desc': 'The id of the media'},
            }
        })

        addApiView('media.delete', self.deleteView, docs = {
            'desc': 'Delete a media from the wanted list',
            'params': {
                'id': {'desc': 'Media ID(s) you want to delete.', 'type': 'int (comma separated)'},
                'delete_from': {'desc': 'Delete media from this page', 'type': 'string: all (default), wanted, manage'},
            }
        })

        addApiView('media.available_chars', self.charView)

        addEvent('app.load', self.addSingleRefreshView, priority = 100)
        addEvent('app.load', self.addSingleListView, priority = 100)
        addEvent('app.load', self.addSingleCharView, priority = 100)
        addEvent('app.load', self.addSingleDeleteView, priority = 100)
        addEvent('app.load', self.cleanupFaults)

        addEvent('media.get', self.get)
        addEvent('media.with_status', self.withStatus)
        addEvent('media.with_identifiers', self.withIdentifiers)
        addEvent('media.list', self.list)
        addEvent('media.delete', self.delete)
        addEvent('media.restatus', self.restatus)
        addEvent('media.tag', self.tag)
        addEvent('media.untag', self.unTag)

    # Wrongly tagged media files
    def cleanupFaults(self):
        medias = fireEvent('media.with_status', 'ignored', single = True) or []

        db = get_db()
        for media in medias:
            try:
                media['status'] = 'done'
                db.update(media)
            except:
                pass

    def refresh(self, id = '', **kwargs):
        handlers = []
        ids = splitString(id)

        for x in ids:

            refresh_handler = self.createRefreshHandler(x)
            if refresh_handler:
                handlers.append(refresh_handler)

        fireEvent('notify.frontend', type = 'media.busy', data = {'_id': ids})
        fireEventAsync('schedule.queue', handlers = handlers)

        return {
            'success': True,
        }

    def createRefreshHandler(self, media_id):

        try:
            media = get_db().get('id', media_id)
            event = '%s.update' % media.get('type')

            def handler():
                fireEvent(event, media_id = media_id, on_complete = self.createOnComplete(media_id))

            return handler

        except:
            log.error('Refresh handler for non existing media: %s', traceback.format_exc())

    def addSingleRefreshView(self):

        for media_type in fireEvent('media.types', merge = True):
            addApiView('%s.refresh' % media_type, self.refresh)

    def get(self, media_id):

        try:
            db = get_db()

            imdb_id = getImdb(str(media_id))

            if imdb_id:
                media = db.get('media', 'imdb-%s' % imdb_id, with_doc = True)['doc']
            else:
                media = db.get('id', media_id)

            if media:

                # Attach category
                try: media['category'] = db.get('id', media.get('category_id'))
                except: pass

                media['releases'] = fireEvent('release.for_media', media['_id'], single = True)

            return media

        except (RecordNotFound, RecordDeleted):
            log.error('Media with id "%s" not found', media_id)
        except:
            raise

    def getView(self, id = None, **kwargs):

        media = self.get(id) if id else None

        return {
            'success': media is not None,
            'media': media,
        }

    def withStatus(self, status, types = None, with_doc = True):

        db = get_db()

        if types and not isinstance(types, (list, tuple)):
            types = [types]

        status = list(status if isinstance(status, (list, tuple)) else [status])

        for s in status:
            for ms in db.get_many('media_status', s):
                if with_doc:
                    try:
                        doc = db.get('id', ms['_id'])

                        if types and doc.get('type') not in types:
                            continue

                        yield doc
                    except (RecordDeleted, RecordNotFound):
                        log.debug('Record not found, skipping: %s', ms['_id'])
                    except (ValueError, EOFError):
                        fireEvent('database.delete_corrupted', ms.get('_id'), traceback_error = traceback.format_exc(0))
                else:
                    yield ms

    def withIdentifiers(self, identifiers, with_doc = False):
        db = get_db()

        for x in identifiers:
            try:
                return db.get('media', '%s-%s' % (x, identifiers[x]), with_doc = with_doc)
            except:
                pass

        log.debug('No media found with identifiers: %s', identifiers)
        return False

    def list(self, types = None, status = None, release_status = None, status_or = False, limit_offset = None, with_tags = None, starts_with = None, search = None):

        db = get_db()

        # Make a list from string
        if status and not isinstance(status, (list, tuple)):
            status = [status]
        if release_status and not isinstance(release_status, (list, tuple)):
            release_status = [release_status]
        if types and not isinstance(types, (list, tuple)):
            types = [types]
        if with_tags and not isinstance(with_tags, (list, tuple)):
            with_tags = [with_tags]

        # query media ids
        if types:
            all_media_ids = set()
            for media_type in types:
                all_media_ids = all_media_ids.union(set([x['_id'] for x in db.get_many('media_by_type', media_type)]))
        else:
            all_media_ids = set([x['_id'] for x in db.all('media')])

        media_ids = list(all_media_ids)
        filter_by = {}

        # Filter on movie status
        if status and len(status) > 0:
            filter_by['media_status'] = set()
            for media_status in fireEvent('media.with_status', status, with_doc = False, single = True):
                filter_by['media_status'].add(media_status.get('_id'))

        # Filter on release status
        if release_status and len(release_status) > 0:
            filter_by['release_status'] = set()
            for release_status in fireEvent('release.with_status', release_status, with_doc = False, single = True):
                filter_by['release_status'].add(release_status.get('media_id'))

        # Add search filters
        if starts_with:
            starts_with = toUnicode(starts_with.lower())[0]
            starts_with = starts_with if starts_with in ascii_lowercase else '#'
            filter_by['starts_with'] = [x['_id'] for x in db.get_many('media_startswith', starts_with)]

        # Add tag filter
        if with_tags:
            filter_by['with_tags'] = set()
            for tag in with_tags:
                for x in db.get_many('media_tag', tag):
                    filter_by['with_tags'].add(x['_id'])

        # Filter with search query
        if search:
            filter_by['search'] = [x['_id'] for x in db.get_many('media_search_title', search)]

        if status_or and 'media_status' in filter_by and 'release_status' in filter_by:
            filter_by['status'] = list(filter_by['media_status']) + list(filter_by['release_status'])
            del filter_by['media_status']
            del filter_by['release_status']

        # Filter by combining ids
        for x in filter_by:
            media_ids = [n for n in media_ids if n in filter_by[x]]

        total_count = len(media_ids)
        if total_count == 0:
            return 0, []

        offset = 0
        limit = -1
        if limit_offset:
            splt = splitString(limit_offset) if isinstance(limit_offset, (str, unicode)) else limit_offset
            limit = tryInt(splt[0])
            offset = tryInt(0 if len(splt) is 1 else splt[1])

        # List movies based on title order
        medias = []
        for m in db.all('media_title'):
            media_id = m['_id']
            if media_id not in media_ids: continue
            if offset > 0:
                offset -= 1
                continue

            media = fireEvent('media.get', media_id, single = True)

            # Skip if no media has been found
            if not media:
                continue

            # Merge releases with movie dict
            medias.append(media)

            # remove from media ids
            media_ids.remove(media_id)
            if len(media_ids) == 0 or len(medias) == limit: break

        return total_count, medias

    def listView(self, **kwargs):

        total_movies, movies = self.list(
            types = splitString(kwargs.get('type')),
            status = splitString(kwargs.get('status')),
            release_status = splitString(kwargs.get('release_status')),
            status_or = kwargs.get('status_or') is not None,
            limit_offset = kwargs.get('limit_offset'),
            with_tags = splitString(kwargs.get('with_tags')),
            starts_with = kwargs.get('starts_with'),
            search = kwargs.get('search')
        )

        return {
            'success': True,
            'empty': len(movies) == 0,
            'total': total_movies,
            'movies': movies,
        }

    def addSingleListView(self):

        for media_type in fireEvent('media.types', merge = True):
            tempList = lambda *args, **kwargs : self.listView(type = media_type, **kwargs)
            addApiView('%s.list' % media_type, tempList, docs = {
                'desc': 'List media',
                'params': {
                    'status': {'type': 'array or csv', 'desc': 'Filter ' + media_type + ' by status. Example:"active,done"'},
                    'release_status': {'type': 'array or csv', 'desc': 'Filter ' + media_type + ' by status of its releases. Example:"snatched,available"'},
                    'limit_offset': {'desc': 'Limit and offset the ' + media_type + ' list. Examples: "50" or "50,30"'},
                    'starts_with': {'desc': 'Starts with these characters. Example: "a" returns all ' + media_type + 's starting with the letter "a"'},
                    'search': {'desc': 'Search ' + media_type + ' title'},
                },
                'return': {'type': 'object', 'example': """{
        'success': True,
        'empty': bool, any """ + media_type + """s returned or not,
        'media': array, media found,
    }"""}
            })

    def availableChars(self, types = None, status = None, release_status = None):

        db = get_db()

        # Make a list from string
        if status and not isinstance(status, (list, tuple)):
            status = [status]
        if release_status and not isinstance(release_status, (list, tuple)):
            release_status = [release_status]
        if types and not isinstance(types, (list, tuple)):
            types = [types]

        # query media ids
        if types:
            all_media_ids = set()
            for media_type in types:
                all_media_ids = all_media_ids.union(set([x['_id'] for x in db.get_many('media_by_type', media_type)]))
        else:
            all_media_ids = set([x['_id'] for x in db.all('media')])

        media_ids = all_media_ids
        filter_by = {}

        # Filter on movie status
        if status and len(status) > 0:
            filter_by['media_status'] = set()
            for media_status in fireEvent('media.with_status', status, with_doc = False, single = True):
                filter_by['media_status'].add(media_status.get('_id'))

        # Filter on release status
        if release_status and len(release_status) > 0:
            filter_by['release_status'] = set()
            for release_status in fireEvent('release.with_status', release_status, with_doc = False, single = True):
                filter_by['release_status'].add(release_status.get('media_id'))

        # Filter by combining ids
        for x in filter_by:
            media_ids = [n for n in media_ids if n in filter_by[x]]

        chars = set()
        for x in db.all('media_startswith'):
            if x['_id'] in media_ids:
                chars.add(x['key'])

            if len(chars) == 27:
                break

        return list(chars)

    def charView(self, **kwargs):

        type = splitString(kwargs.get('type', 'movie'))
        status = splitString(kwargs.get('status', None))
        release_status = splitString(kwargs.get('release_status', None))
        chars = self.availableChars(type, status, release_status)

        return {
            'success': True,
            'empty': len(chars) == 0,
            'chars': chars,
        }

    def addSingleCharView(self):

        for media_type in fireEvent('media.types', merge = True):
            tempChar = lambda *args, **kwargs : self.charView(type = media_type, **kwargs)
            addApiView('%s.available_chars' % media_type, tempChar)

    def delete(self, media_id, delete_from = None):

        try:
            db = get_db()

            media = db.get('id', media_id)
            if media:
                deleted = False

                media_releases = fireEvent('release.for_media', media['_id'], single = True)

                if delete_from == 'all':
                    # Delete connected releases
                    for release in media_releases:
                        db.delete(release)

                    db.delete(media)
                    deleted = True
                else:

                    total_releases = len(media_releases)
                    total_deleted = 0
                    new_media_status = None

                    for release in media_releases:
                        if delete_from in ['wanted', 'snatched', 'late']:
                            if release.get('status') != 'done':
                                db.delete(release)
                                total_deleted += 1
                            new_media_status = 'done'
                        elif delete_from == 'manage':
                            if release.get('status') == 'done' or media.get('status') == 'done':
                                db.delete(release)
                                total_deleted += 1

                    if (total_releases == total_deleted) or (total_releases == 0 and not new_media_status) or (not new_media_status and delete_from == 'late'):
                        db.delete(media)
                        deleted = True
                    elif new_media_status:
                        media['status'] = new_media_status

                        # Remove profile (no use for in manage)
                        if new_media_status == 'done':
                            media['profile_id'] = None
                        
                        db.update(media)

                        fireEvent('media.untag', media['_id'], 'recent', single = True)
                    else:
                        fireEvent('media.restatus', media.get('_id'), single = True)

                if deleted:
                    fireEvent('notify.frontend', type = 'media.deleted', data = media)
        except:
            log.error('Failed deleting media: %s', traceback.format_exc())

        return True

    def deleteView(self, id = '', **kwargs):

        ids = splitString(id)
        for media_id in ids:
            self.delete(media_id, delete_from = kwargs.get('delete_from', 'all'))

        return {
            'success': True,
        }

    def addSingleDeleteView(self):

        for media_type in fireEvent('media.types', merge = True):
            tempDelete = lambda *args, **kwargs : self.deleteView(type = media_type, **kwargs)
            addApiView('%s.delete' % media_type, tempDelete, docs = {
            'desc': 'Delete a ' + media_type + ' from the wanted list',
            'params': {
                'id': {'desc': 'Media ID(s) you want to delete.', 'type': 'int (comma separated)'},
                'delete_from': {'desc': 'Delete ' + media_type + ' from this page', 'type': 'string: all (default), wanted, manage'},
            }
        })

    def restatus(self, media_id, tag_recent = True, allowed_restatus = None):

        try:
            db = get_db()

            m = db.get('id', media_id)
            previous_status = m['status']

            log.debug('Changing status for %s', getTitle(m))
            if not m['profile_id']:
                m['status'] = 'done'
            else:
                m['status'] = 'active'

                try:
                    profile = db.get('id', m['profile_id'])
                    media_releases = fireEvent('release.for_media', m['_id'], single = True)
                    done_releases = [release for release in media_releases if release.get('status') == 'done']

                    if done_releases:

                        # Check if we are finished with the media
                        for release in done_releases:
                            if fireEvent('quality.isfinish', {'identifier': release['quality'], 'is_3d': release.get('is_3d', False)}, profile, timedelta(seconds = time.time() - release['last_edit']).days, single = True):
                                m['status'] = 'done'
                                break

                    elif previous_status == 'done':
                        m['status'] = 'done'

                except RecordNotFound:
                    log.debug('Failed restatus, keeping previous: %s', traceback.format_exc())
                    m['status'] = previous_status

            # Only update when status has changed
            if previous_status != m['status'] and (not allowed_restatus or m['status'] in allowed_restatus):
                db.update(m)

                # Tag media as recent
                if tag_recent:
                    self.tag(media_id, 'recent', update_edited = True)

            return m['status']
        except:
            log.error('Failed restatus: %s', traceback.format_exc())

    def tag(self, media_id, tag, update_edited = False):

        try:
            db = get_db()
            m = db.get('id', media_id)

            if update_edited:
                m['last_edit'] = int(time.time())

            tags = m.get('tags') or []
            if tag not in tags:
                tags.append(tag)
                m['tags'] = tags
                db.update(m)

            return True
        except:
            log.error('Failed tagging: %s', traceback.format_exc())

        return False

    def unTag(self, media_id, tag):

        try:
            db = get_db()
            m = db.get('id', media_id)

            tags = m.get('tags') or []
            if tag in tags:
                new_tags = list(set(tags))
                new_tags.remove(tag)

                m['tags'] = new_tags
                db.update(m)

            return True
        except:
            log.error('Failed untagging: %s', traceback.format_exc())

        return False

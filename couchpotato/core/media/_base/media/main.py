from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import mergeDicts, splitString, getImdb
from couchpotato.core.logger import CPLog
from couchpotato.core.media import MediaBase
from couchpotato.core.settings.model import Library, LibraryTitle, Release, \
    Media
from sqlalchemy.orm import joinedload_all
from sqlalchemy.sql.expression import or_, asc, not_, desc
from string import ascii_lowercase

log = CPLog(__name__)


class MediaPlugin(MediaBase):

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
                'status': {'type': 'array or csv', 'desc': 'Filter movie by status. Example:"active,done"'},
                'release_status': {'type': 'array or csv', 'desc': 'Filter movie by status of its releases. Example:"snatched,available"'},
                'limit_offset': {'desc': 'Limit and offset the movie list. Examples: "50" or "50,30"'},
                'starts_with': {'desc': 'Starts with these characters. Example: "a" returns all movies starting with the letter "a"'},
                'search': {'desc': 'Search movie title'},
            },
            'return': {'type': 'object', 'example': """{
    'success': True,
    'empty': bool, any movies returned or not,
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

        addEvent('app.load', self.addSingleRefreshView)
        addEvent('app.load', self.addSingleListView)
        addEvent('app.load', self.addSingleCharView)
        addEvent('app.load', self.addSingleDeleteView)

        addEvent('media.get', self.get)
        addEvent('media.list', self.list)
        addEvent('media.delete', self.delete)
        addEvent('media.restatus', self.restatus)

    def refresh(self, id = '', **kwargs):
        db = get_session()

        for x in splitString(id):
            media = db.query(Media).filter_by(id = x).first()

            if media:
                # Get current selected title
                default_title = ''
                for title in media.library.titles:
                    if title.default: default_title = title.title

                fireEvent('notify.frontend', type = '%s.busy' % media.type, data = {'id': x})
                fireEventAsync('library.update.%s' % media.type, identifier = media.library.identifier, default_title = default_title, force = True, on_complete = self.createOnComplete(x))

        db.expire_all()

        return {
            'success': True,
        }

    def addSingleRefreshView(self):

        for media_type in fireEvent('media.types', merge = True):
            addApiView('%s.refresh' % media_type, self.refresh)

    def get(self, media_id):

        db = get_session()

        imdb_id = getImdb(str(media_id))

        if imdb_id:
            m = db.query(Media).filter(Media.library.has(identifier = imdb_id)).first()
        else:
            m = db.query(Media).filter_by(id = media_id).first()

        results = None
        if m:
            results = m.to_dict(self.default_dict)

        db.expire_all()
        return results

    def getView(self, id = None, **kwargs):

        media = self.get(id) if id else None

        return {
            'success': media is not None,
            'media': media,
        }

    def list(self, types = None, status = None, release_status = None, limit_offset = None, starts_with = None, search = None, order = None):

        db = get_session()

        # Make a list from string
        if status and not isinstance(status, (list, tuple)):
            status = [status]
        if release_status and not isinstance(release_status, (list, tuple)):
            release_status = [release_status]
        if types and not isinstance(types, (list, tuple)):
            types = [types]

        # query movie ids
        q = db.query(Media) \
            .with_entities(Media.id) \
            .group_by(Media.id)

        # Filter on movie status
        if status and len(status) > 0:
            statuses = fireEvent('status.get', status, single = len(status) > 1)
            statuses = [s.get('id') for s in statuses]

            q = q.filter(Media.status_id.in_(statuses))

        # Filter on release status
        if release_status and len(release_status) > 0:
            q = q.join(Media.releases)

            statuses = fireEvent('status.get', release_status, single = len(release_status) > 1)
            statuses = [s.get('id') for s in statuses]

            q = q.filter(Release.status_id.in_(statuses))

        # Filter on type
        if types and len(types) > 0:
            try: q = q.filter(Media.type.in_(types))
            except: pass

        # Only join when searching / ordering
        if starts_with or search or order != 'release_order':
            q = q.join(Media.library, Library.titles) \
                .filter(LibraryTitle.default == True)

        # Add search filters
        filter_or = []
        if starts_with:
            starts_with = toUnicode(starts_with.lower())
            if starts_with in ascii_lowercase:
                filter_or.append(LibraryTitle.simple_title.startswith(starts_with))
            else:
                ignore = []
                for letter in ascii_lowercase:
                    ignore.append(LibraryTitle.simple_title.startswith(toUnicode(letter)))
                filter_or.append(not_(or_(*ignore)))

        if search:
            filter_or.append(LibraryTitle.simple_title.like('%%' + search + '%%'))

        if len(filter_or) > 0:
            q = q.filter(or_(*filter_or))

        total_count = q.count()
        if total_count == 0:
            return 0, []

        if order == 'release_order':
            q = q.order_by(desc(Release.last_edit))
        else:
            q = q.order_by(asc(LibraryTitle.simple_title))

        if limit_offset:
            splt = splitString(limit_offset) if isinstance(limit_offset, (str, unicode)) else limit_offset
            limit = splt[0]
            offset = 0 if len(splt) is 1 else splt[1]
            q = q.limit(limit).offset(offset)

        # Get all media_ids in sorted order
        media_ids = [m.id for m in q.all()]

        # List release statuses
        releases = db.query(Release) \
            .filter(Release.movie_id.in_(media_ids)) \
            .all()

        release_statuses = dict((m, set()) for m in media_ids)
        releases_count = dict((m, 0) for m in media_ids)
        for release in releases:
            release_statuses[release.movie_id].add('%d,%d' % (release.status_id, release.quality_id))
            releases_count[release.movie_id] += 1

        # Get main movie data
        q2 = db.query(Media) \
            .options(joinedload_all('library.titles')) \
            .options(joinedload_all('library.files')) \
            .options(joinedload_all('status')) \
            .options(joinedload_all('files'))

        q2 = q2.filter(Media.id.in_(media_ids))

        results = q2.all()

        # Create dict by movie id
        movie_dict = {}
        for movie in results:
            movie_dict[movie.id] = movie

        # List movies based on media_ids order
        movies = []
        for media_id in media_ids:

            releases = []
            for r in release_statuses.get(media_id):
                x = splitString(r)
                releases.append({'status_id': x[0], 'quality_id': x[1]})

            # Merge releases with movie dict
            movies.append(mergeDicts(movie_dict[media_id].to_dict({
                'library': {'titles': {}, 'files':{}},
                'files': {},
            }), {
                'releases': releases,
                'releases_count': releases_count.get(media_id),
            }))

        db.expire_all()
        return total_count, movies

    def listView(self, **kwargs):

        types = splitString(kwargs.get('types'))
        status = splitString(kwargs.get('status'))
        release_status = splitString(kwargs.get('release_status'))
        limit_offset = kwargs.get('limit_offset')
        starts_with = kwargs.get('starts_with')
        search = kwargs.get('search')
        order = kwargs.get('order')

        total_movies, movies = self.list(
            types = types,
            status = status,
            release_status = release_status,
            limit_offset = limit_offset,
            starts_with = starts_with,
            search = search,
            order = order
        )

        return {
            'success': True,
            'empty': len(movies) == 0,
            'total': total_movies,
            'movies': movies,
        }

    def addSingleListView(self):

        for media_type in fireEvent('media.types', merge = True):
            def tempList(*args, **kwargs):
                return self.listView(types = media_type, *args, **kwargs)
            addApiView('%s.list' % media_type, tempList)

    def availableChars(self, types = None, status = None, release_status = None):

        types = types or []
        status = status or []
        release_status = release_status or []

        db = get_session()

        # Make a list from string
        if not isinstance(status, (list, tuple)):
            status = [status]
        if release_status and not isinstance(release_status, (list, tuple)):
            release_status = [release_status]
        if types and not isinstance(types, (list, tuple)):
            types = [types]

        q = db.query(Media)

        # Filter on movie status
        if status and len(status) > 0:
            statuses = fireEvent('status.get', status, single = len(release_status) > 1)
            statuses = [s.get('id') for s in statuses]

            q = q.filter(Media.status_id.in_(statuses))

        # Filter on release status
        if release_status and len(release_status) > 0:

            statuses = fireEvent('status.get', release_status, single = len(release_status) > 1)
            statuses = [s.get('id') for s in statuses]

            q = q.join(Media.releases) \
                .filter(Release.status_id.in_(statuses))

        # Filter on type
        if types and len(types) > 0:
            try: q = q.filter(Media.type.in_(types))
            except: pass

        q = q.join(Library, LibraryTitle) \
            .with_entities(LibraryTitle.simple_title) \
            .filter(LibraryTitle.default == True)

        titles = q.all()

        chars = set()
        for title in titles:
            try:
                char = title[0][0]
                char = char if char in ascii_lowercase else '#'
                chars.add(str(char))
            except:
                log.error('Failed getting title for %s', title.libraries_id)

            if len(chars) == 25:
                break

        db.expire_all()
        return ''.join(sorted(chars))

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
            def tempChar(*args, **kwargs):
                return self.charView(types = media_type, *args, **kwargs)
            addApiView('%s.available_chars' % media_type, tempChar)

    def delete(self, media_id, delete_from = None):

        db = get_session()

        media = db.query(Media).filter_by(id = media_id).first()
        if media:
            deleted = False
            if delete_from == 'all':
                db.delete(media)
                db.commit()
                deleted = True
            else:
                done_status = fireEvent('status.get', 'done', single = True)

                total_releases = len(media.releases)
                total_deleted = 0
                new_movie_status = None
                for release in media.releases:
                    if delete_from in ['wanted', 'snatched', 'late']:
                        if release.status_id != done_status.get('id'):
                            db.delete(release)
                            total_deleted += 1
                        new_movie_status = 'done'
                    elif delete_from == 'manage':
                        if release.status_id == done_status.get('id'):
                            db.delete(release)
                            total_deleted += 1
                        new_movie_status = 'active'
                db.commit()

                if total_releases == total_deleted:
                    db.delete(media)
                    db.commit()
                    deleted = True
                elif new_movie_status:
                    new_status = fireEvent('status.get', new_movie_status, single = True)
                    media.profile_id = None
                    media.status_id = new_status.get('id')
                    db.commit()
                else:
                    fireEvent('media.restatus', media.id, single = True)

            if deleted:
                fireEvent('notify.frontend', type = 'movie.deleted', data = media.to_dict())

        db.expire_all()
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
            def tempDelete(*args, **kwargs):
                return self.deleteView(types = media_type, *args, **kwargs)
            addApiView('%s.delete' % media_type, tempDelete)

    def restatus(self, media_id):

        active_status, done_status = fireEvent('status.get', ['active', 'done'], single = True)

        db = get_session()

        m = db.query(Media).filter_by(id = media_id).first()
        if not m or len(m.library.titles) == 0:
            log.debug('Can\'t restatus movie, doesn\'t seem to exist.')
            return False

        log.debug('Changing status for %s', m.library.titles[0].title)
        if not m.profile:
            m.status_id = done_status.get('id')
        else:
            move_to_wanted = True

            for t in m.profile.types:
                for release in m.releases:
                    if t.quality.identifier is release.quality.identifier and (release.status_id is done_status.get('id') and t.finish):
                        move_to_wanted = False

            m.status_id = active_status.get('id') if move_to_wanted else done_status.get('id')

        db.commit()

        return True


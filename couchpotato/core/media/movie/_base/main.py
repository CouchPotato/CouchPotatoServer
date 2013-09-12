from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.encoding import toUnicode, simplifyString
from couchpotato.core.helpers.variable import getImdb, splitString, tryInt, \
    mergeDicts
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie import MovieTypeBase
from couchpotato.core.settings.model import Library, LibraryTitle, Media, \
    Release
from couchpotato.environment import Env
from sqlalchemy.orm import joinedload_all
from sqlalchemy.sql.expression import or_, asc, not_, desc
from string import ascii_lowercase
import time

log = CPLog(__name__)


class MovieBase(MovieTypeBase):

    default_dict = {
        'profile': {'types': {'quality': {}}},
        'releases': {'status': {}, 'quality': {}, 'files':{}, 'info': {}},
        'library': {'titles': {}, 'files':{}},
        'files': {},
        'status': {},
        'category': {},
    }

    def __init__(self):

        # Initialize this type
        super(MovieBase, self).__init__()
        self.initType()

        addApiView('movie.search', self.search, docs = {
            'desc': 'Search the movie providers for a movie',
            'params': {
                'q': {'desc': 'The (partial) movie name you want to search for'},
            },
            'return': {'type': 'object', 'example': """{
    'success': True,
    'empty': bool, any movies returned or not,
    'movies': array, movies found,
}"""}
        })
        addApiView('movie.list', self.listView, docs = {
            'desc': 'List movies in wanted list',
            'params': {
                'status': {'type': 'array or csv', 'desc': 'Filter movie by status. Example:"active,done"'},
                'release_status': {'type': 'array or csv', 'desc': 'Filter movie by status of its releases. Example:"snatched,available"'},
                'limit_offset': {'desc': 'Limit and offset the movie list. Examples: "50" or "50,30"'},
                'starts_with': {'desc': 'Starts with these characters. Example: "a" returns all movies starting with the letter "a"'},
                'search': {'desc': 'Search movie title'},
            },
            'return': {'type': 'object', 'example': """{
    'success': True,
    'empty': bool, any movies returned or not,
    'movies': array, movies found,
}"""}
        })
        addApiView('movie.get', self.getView, docs = {
            'desc': 'Get a movie by id',
            'params': {
                'id': {'desc': 'The id of the movie'},
            }
        })
        addApiView('movie.refresh', self.refresh, docs = {
            'desc': 'Refresh a movie by id',
            'params': {
                'id': {'desc': 'Movie ID(s) you want to refresh.', 'type': 'int (comma separated)'},
            }
        })
        addApiView('movie.available_chars', self.charView)
        addApiView('movie.add', self.addView, docs = {
            'desc': 'Add new movie to the wanted list',
            'params': {
                'identifier': {'desc': 'IMDB id of the movie your want to add.'},
                'profile_id': {'desc': 'ID of quality profile you want the add the movie in. If empty will use the default profile.'},
                'title': {'desc': 'Movie title to use for searches. Has to be one of the titles returned by movie.search.'},
            }
        })
        addApiView('movie.edit', self.edit, docs = {
            'desc': 'Add new movie to the wanted list',
            'params': {
                'id': {'desc': 'Movie ID(s) you want to edit.', 'type': 'int (comma separated)'},
                'profile_id': {'desc': 'ID of quality profile you want the edit the movie to.'},
                'default_title': {'desc': 'Movie title to use for searches. Has to be one of the titles returned by movie.search.'},
            }
        })
        addApiView('movie.delete', self.deleteView, docs = {
            'desc': 'Delete a movie from the wanted list',
            'params': {
                'id': {'desc': 'Movie ID(s) you want to delete.', 'type': 'int (comma separated)'},
                'delete_from': {'desc': 'Delete movie from this page', 'type': 'string: all (default), wanted, manage'},
            }
        })

        addEvent('movie.add', self.add)
        addEvent('movie.delete', self.delete)
        addEvent('movie.get', self.get)
        addEvent('movie.list', self.list)
        addEvent('movie.restatus', self.restatus)

        # Clean releases that didn't have activity in the last week
        addEvent('app.load', self.cleanReleases)
        fireEvent('schedule.interval', 'movie.clean_releases', self.cleanReleases, hours = 4)

    def cleanReleases(self):

        log.debug('Removing releases from dashboard')

        now = time.time()
        week = 262080

        done_status, available_status, snatched_status = \
            fireEvent('status.get', ['done', 'available', 'snatched'], single = True)

        db = get_session()

        # get movies last_edit more than a week ago
        movies = db.query(Media) \
            .filter(Media.status_id == done_status.get('id'), Media.last_edit < (now - week)) \
            .all()

        for movie in movies:
            for rel in movie.releases:
                if rel.status_id in [available_status.get('id'), snatched_status.get('id')]:
                    fireEvent('release.delete', id = rel.id, single = True)

        db.expire_all()

    def getView(self, id = None, **kwargs):

        movie = self.get(id) if id else None

        return {
            'success': movie is not None,
            'movie': movie,
        }

    def get(self, movie_id):

        db = get_session()

        imdb_id = getImdb(str(movie_id))

        if(imdb_id):
            m = db.query(Media).filter(Media.library.has(identifier = imdb_id)).first()
        else:
            m = db.query(Media).filter_by(id = movie_id).first()

        results = None
        if m:
            results = m.to_dict(self.default_dict)

        db.expire_all()
        return results

    def list(self, status = None, release_status = None, limit_offset = None, starts_with = None, search = None, order = None):

        db = get_session()

        # Make a list from string
        if status and not isinstance(status, (list, tuple)):
            status = [status]
        if release_status and not isinstance(release_status, (list, tuple)):
            release_status = [release_status]

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

        # Get all movie_ids in sorted order
        movie_ids = [m.id for m in q.all()]

        # List release statuses
        releases = db.query(Release) \
            .filter(Release.movie_id.in_(movie_ids)) \
            .all()

        release_statuses = dict((m, set()) for m in movie_ids)
        releases_count = dict((m, 0) for m in movie_ids)
        for release in releases:
            release_statuses[release.movie_id].add('%d,%d' % (release.status_id, release.quality_id))
            releases_count[release.movie_id] += 1

        # Get main movie data
        q2 = db.query(Media) \
            .options(joinedload_all('library.titles')) \
            .options(joinedload_all('library.files')) \
            .options(joinedload_all('status')) \
            .options(joinedload_all('files'))

        q2 = q2.filter(Media.id.in_(movie_ids))

        results = q2.all()

        # Create dict by movie id
        movie_dict = {}
        for movie in results:
            movie_dict[movie.id] = movie

        # List movies based on movie_ids order
        movies = []
        for movie_id in movie_ids:

            releases = []
            for r in release_statuses.get(movie_id):
                x = splitString(r)
                releases.append({'status_id': x[0], 'quality_id': x[1]})

            # Merge releases with movie dict
            movies.append(mergeDicts(movie_dict[movie_id].to_dict({
                'library': {'titles': {}, 'files':{}},
                'files': {},
            }), {
                'releases': releases,
                'releases_count': releases_count.get(movie_id),
            }))

        db.expire_all()
        return total_count, movies

    def availableChars(self, status = None, release_status = None):

        status = status or []
        release_status = release_status or []

        db = get_session()

        # Make a list from string
        if not isinstance(status, (list, tuple)):
            status = [status]
        if release_status and not isinstance(release_status, (list, tuple)):
            release_status = [release_status]

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

    def listView(self, **kwargs):

        status = splitString(kwargs.get('status'))
        release_status = splitString(kwargs.get('release_status'))
        limit_offset = kwargs.get('limit_offset')
        starts_with = kwargs.get('starts_with')
        search = kwargs.get('search')
        order = kwargs.get('order')

        total_movies, movies = self.list(
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

    def charView(self, **kwargs):

        status = splitString(kwargs.get('status', None))
        release_status = splitString(kwargs.get('release_status', None))
        chars = self.availableChars(status, release_status)

        return {
            'success': True,
            'empty': len(chars) == 0,
            'chars': chars,
        }

    def refresh(self, id = '', **kwargs):

        db = get_session()

        for x in splitString(id):
            movie = db.query(Media).filter_by(id = x).first()

            if movie:

                # Get current selected title
                default_title = ''
                for title in movie.library.titles:
                    if title.default: default_title = title.title

                fireEvent('notify.frontend', type = 'movie.busy.%s' % x, data = True)
                fireEventAsync('library.update.movie', identifier = movie.library.identifier, default_title = default_title, force = True, on_complete = self.createOnComplete(x))

        db.expire_all()
        return {
            'success': True,
        }

    def search(self, q = '', **kwargs):

        cache_key = u'%s/%s' % (__name__, simplifyString(q))
        movies = Env.get('cache').get(cache_key)

        if not movies:

            if getImdb(q):
                movies = [fireEvent('movie.info', identifier = q, merge = True)]
            else:
                movies = fireEvent('movie.search', q = q, merge = True)
            Env.get('cache').set(cache_key, movies)

        return {
            'success': True,
            'empty': len(movies) == 0 if movies else 0,
            'movies': movies,
        }

    def add(self, params = None, force_readd = True, search_after = True, update_library = False, status_id = None):
        if not params: params = {}

        if not params.get('identifier'):
            msg = 'Can\'t add movie without imdb identifier.'
            log.error(msg)
            fireEvent('notify.frontend', type = 'movie.is_tvshow', message = msg)
            return False
        else:
            try:
                is_movie = fireEvent('movie.is_movie', identifier = params.get('identifier'), single = True)
                if not is_movie:
                    msg = 'Can\'t add movie, seems to be a TV show.'
                    log.error(msg)
                    fireEvent('notify.frontend', type = 'movie.is_tvshow', message = msg)
                    return False
            except:
                pass


        library = fireEvent('library.add.movie', single = True, attrs = params, update_after = update_library)

        # Status
        status_active, snatched_status, ignored_status, done_status, downloaded_status = \
            fireEvent('status.get', ['active', 'snatched', 'ignored', 'done', 'downloaded'], single = True)

        default_profile = fireEvent('profile.default', single = True)
        cat_id = params.get('category_id')

        db = get_session()
        m = db.query(Media).filter_by(library_id = library.get('id')).first()
        added = True
        do_search = False
        search_after = search_after and self.conf('search_on_add', section = 'moviesearcher')
        if not m:
            m = Media(
                library_id = library.get('id'),
                profile_id = params.get('profile_id', default_profile.get('id')),
                status_id = status_id if status_id else status_active.get('id'),
                category_id = tryInt(cat_id) if cat_id is not None and tryInt(cat_id) > 0 else None,
            )
            db.add(m)
            db.commit()

            onComplete = None
            if search_after:
                onComplete = self.createOnComplete(m.id)

            fireEventAsync('library.update.movie', params.get('identifier'), default_title = params.get('title', ''), on_complete = onComplete)
            search_after = False
        elif force_readd:

            # Clean snatched history
            for release in m.releases:
                if release.status_id in [downloaded_status.get('id'), snatched_status.get('id'), done_status.get('id')]:
                    if params.get('ignore_previous', False):
                        release.status_id = ignored_status.get('id')
                    else:
                        fireEvent('release.delete', release.id, single = True)

            m.profile_id = params.get('profile_id', default_profile.get('id'))
            m.category_id = tryInt(cat_id) if cat_id is not None and tryInt(cat_id) > 0 else None
        else:
            log.debug('Movie already exists, not updating: %s', params)
            added = False

        if force_readd:
            m.status_id = status_id if status_id else status_active.get('id')
            m.last_edit = int(time.time())
            do_search = True

        db.commit()

        # Remove releases
        available_status = fireEvent('status.get', 'available', single = True)
        for rel in m.releases:
            if rel.status_id is available_status.get('id'):
                db.delete(rel)
                db.commit()

        movie_dict = m.to_dict(self.default_dict)

        if do_search and search_after:
            onComplete = self.createOnComplete(m.id)
            onComplete()

        if added:
            fireEvent('notify.frontend', type = 'movie.added', data = movie_dict, message = 'Successfully added "%s" to your wanted list.' % params.get('title', ''))

        db.expire_all()
        return movie_dict


    def addView(self, **kwargs):

        movie_dict = self.add(params = kwargs)

        return {
            'success': True,
            'added': True if movie_dict else False,
            'movie': movie_dict,
        }

    def edit(self, id = '', **kwargs):

        db = get_session()

        available_status = fireEvent('status.get', 'available', single = True)

        ids = splitString(id)
        for movie_id in ids:

            m = db.query(Media).filter_by(id = movie_id).first()
            if not m:
                continue

            m.profile_id = kwargs.get('profile_id')

            cat_id = kwargs.get('category_id')
            if cat_id is not None:
                m.category_id = tryInt(cat_id) if tryInt(cat_id) > 0 else None

            # Remove releases
            for rel in m.releases:
                if rel.status_id is available_status.get('id'):
                    db.delete(rel)
                    db.commit()

            # Default title
            if kwargs.get('default_title'):
                for title in m.library.titles:
                    title.default = toUnicode(kwargs.get('default_title', '')).lower() == toUnicode(title.title).lower()

            db.commit()

            fireEvent('movie.restatus', m.id)

            movie_dict = m.to_dict(self.default_dict)
            fireEventAsync('movie.searcher.single', movie_dict, on_complete = self.createNotifyFront(movie_id))

        db.expire_all()
        return {
            'success': True,
        }

    def deleteView(self, id = '', **kwargs):

        ids = splitString(id)
        for movie_id in ids:
            self.delete(movie_id, delete_from = kwargs.get('delete_from', 'all'))

        return {
            'success': True,
        }

    def delete(self, movie_id, delete_from = None):

        db = get_session()

        movie = db.query(Media).filter_by(id = movie_id).first()
        if movie:
            deleted = False
            if delete_from == 'all':
                db.delete(movie)
                db.commit()
                deleted = True
            else:
                done_status = fireEvent('status.get', 'done', single = True)

                total_releases = len(movie.releases)
                total_deleted = 0
                new_movie_status = None
                for release in movie.releases:
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
                    db.delete(movie)
                    db.commit()
                    deleted = True
                elif new_movie_status:
                    new_status = fireEvent('status.get', new_movie_status, single = True)
                    movie.profile_id = None
                    movie.status_id = new_status.get('id')
                    db.commit()
                else:
                    fireEvent('movie.restatus', movie.id, single = True)

            if deleted:
                fireEvent('notify.frontend', type = 'movie.deleted', data = movie.to_dict())

        db.expire_all()
        return True

    def restatus(self, movie_id):

        active_status, done_status = fireEvent('status.get', ['active', 'done'], single = True)

        db = get_session()

        m = db.query(Media).filter_by(id = movie_id).first()
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

    def createOnComplete(self, movie_id):

        def onComplete():
            db = get_session()
            movie = db.query(Media).filter_by(id = movie_id).first()
            fireEventAsync('movie.searcher.single', movie.to_dict(self.default_dict), on_complete = self.createNotifyFront(movie_id))
            db.expire_all()

        return onComplete


    def createNotifyFront(self, movie_id):

        def notifyFront():
            db = get_session()
            movie = db.query(Media).filter_by(id = movie_id).first()
            fireEvent('notify.frontend', type = 'movie.update.%s' % movie.id, data = movie.to_dict(self.default_dict))
            db.expire_all()

        return notifyFront

from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.encoding import toUnicode, simplifyString
from couchpotato.core.helpers.request import getParams, jsonified, getParam
from couchpotato.core.helpers.variable import getImdb, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Library, LibraryTitle, Movie, \
    Release
from couchpotato.environment import Env
from sqlalchemy.orm import joinedload_all
from sqlalchemy.sql.expression import or_, asc, not_, desc
from string import ascii_lowercase
import time

log = CPLog(__name__)


class MoviePlugin(Plugin):

    default_dict = {
        'profile': {'types': {'quality': {}}},
        'releases': {'status': {}, 'quality': {}, 'files':{}, 'info': {}},
        'library': {'titles': {}, 'files':{}},
        'files': {},
        'status': {}
    }

    def __init__(self):
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
        movies = db.query(Movie) \
            .filter(Movie.status_id == done_status.get('id'), Movie.last_edit < (now - week)) \
            .all()

        for movie in movies:
            for rel in movie.releases:
                if rel.status_id in [available_status.get('id'), snatched_status.get('id')]:
                    fireEvent('release.delete', id = rel.id, single = True)

        db.expire_all()

    def getView(self):

        movie_id = getParam('id')
        movie = self.get(movie_id) if movie_id else None

        return jsonified({
            'success': movie is not None,
            'movie': movie,
        })

    def get(self, movie_id):

        db = get_session()

        imdb_id = getImdb(str(movie_id))

        if(imdb_id):
            m = db.query(Movie).filter(Movie.library.has(identifier = imdb_id)).first()
        else:
            m = db.query(Movie).filter_by(id = movie_id).first()

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

        q = db.query(Movie) \
            .outerjoin(Movie.releases, Movie.library, Library.titles) \
            .filter(LibraryTitle.default == True) \
            .group_by(Movie.id)

        # Filter on movie status
        if status and len(status) > 0:
            q = q.filter(or_(*[Movie.status.has(identifier = s) for s in status]))

        # Filter on release status
        if release_status and len(release_status) > 0:
            q = q.filter(or_(*[Release.status.has(identifier = s) for s in release_status]))

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

        if filter_or:
            q = q.filter(or_(*filter_or))

        total_count = q.count()

        if order == 'release_order':
            q = q.order_by(desc(Release.last_edit))
        else:
            q = q.order_by(asc(LibraryTitle.simple_title))

        q = q.subquery()
        q2 = db.query(Movie).join((q, q.c.id == Movie.id)) \
            .options(joinedload_all('releases')) \
            .options(joinedload_all('profile.types')) \
            .options(joinedload_all('library.titles')) \
            .options(joinedload_all('library.files')) \
            .options(joinedload_all('status')) \
            .options(joinedload_all('files'))

        if limit_offset:
            splt = splitString(limit_offset) if isinstance(limit_offset, (str, unicode)) else limit_offset
            limit = splt[0]
            offset = 0 if len(splt) is 1 else splt[1]
            q2 = q2.limit(limit).offset(offset)

        results = q2.all()
        movies = []
        for movie in results:
            movies.append(movie.to_dict({
                'profile': {'types': {}},
                'releases': {'files':{}, 'info': {}},
                'library': {'titles': {}, 'files':{}},
                'files': {},
            }))

        db.expire_all()
        return (total_count, movies)

    def availableChars(self, status = None, release_status = None):

        chars = ''

        db = get_session()

        # Make a list from string
        if not isinstance(status, (list, tuple)):
            status = [status]
        if release_status and not isinstance(release_status, (list, tuple)):
            release_status = [release_status]

        q = db.query(Movie) \
            .outerjoin(Movie.releases, Movie.library, Library.titles, Movie.status) \
            .options(joinedload_all('library.titles'))

        # Filter on movie status
        if status and len(status) > 0:
            q = q.filter(or_(*[Movie.status.has(identifier = s) for s in status]))

        # Filter on release status
        if release_status and len(release_status) > 0:
            q = q.filter(or_(*[Release.status.has(identifier = s) for s in release_status]))

        results = q.all()

        for movie in results:
            char = movie.library.titles[0].simple_title[0]
            char = char if char in ascii_lowercase else '#'
            if char not in chars:
                chars += str(char)

        db.expire_all()
        return ''.join(sorted(chars, key = str.lower))

    def listView(self):

        params = getParams()
        status = splitString(params.get('status', None))
        release_status = splitString(params.get('release_status', None))
        limit_offset = params.get('limit_offset', None)
        starts_with = params.get('starts_with', None)
        search = params.get('search', None)
        order = params.get('order', None)

        total_movies, movies = self.list(
            status = status,
            release_status = release_status,
            limit_offset = limit_offset,
            starts_with = starts_with,
            search = search,
            order = order
        )

        return jsonified({
            'success': True,
            'empty': len(movies) == 0,
            'total': total_movies,
            'movies': movies,
        })

    def charView(self):

        params = getParams()
        status = splitString(params.get('status', None))
        release_status = splitString(params.get('release_status', None))
        chars = self.availableChars(status, release_status)

        return jsonified({
            'success': True,
            'empty': len(chars) == 0,
            'chars': chars,
        })

    def refresh(self):

        db = get_session()

        for id in splitString(getParam('id')):
            movie = db.query(Movie).filter_by(id = id).first()

            if movie:

                # Get current selected title
                default_title = ''
                for title in movie.library.titles:
                    if title.default: default_title = title.title

                fireEvent('notify.frontend', type = 'movie.busy.%s' % id, data = True)
                fireEventAsync('library.update', identifier = movie.library.identifier, default_title = default_title, force = True, on_complete = self.createOnComplete(id))

        db.expire_all()
        return jsonified({
            'success': True,
        })

    def search(self):

        q = getParam('q')
        cache_key = u'%s/%s' % (__name__, simplifyString(q))
        movies = Env.get('cache').get(cache_key)

        if not movies:

            if getImdb(q):
                movies = [fireEvent('movie.info', identifier = q, merge = True)]
            else:
                movies = fireEvent('movie.search', q = q, merge = True)
            Env.get('cache').set(cache_key, movies)

        return jsonified({
            'success': True,
            'empty': len(movies) == 0 if movies else 0,
            'movies': movies,
        })

    def add(self, params = {}, force_readd = True, search_after = True, update_library = False, status_id = None):

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


        library = fireEvent('library.add', single = True, attrs = params, update_after = update_library)

        # Status
        status_active, snatched_status, ignored_status, done_status, downloaded_status = \
            fireEvent('status.get', ['active', 'snatched', 'ignored', 'done', 'downloaded'], single = True)

        default_profile = fireEvent('profile.default', single = True)

        db = get_session()
        m = db.query(Movie).filter_by(library_id = library.get('id')).first()
        added = True
        do_search = False
        if not m:
            m = Movie(
                library_id = library.get('id'),
                profile_id = params.get('profile_id', default_profile.get('id')),
                status_id = status_id if status_id else status_active.get('id'),
            )
            db.add(m)
            db.commit()

            onComplete = None
            if search_after:
                onComplete = self.createOnComplete(m.id)

            fireEventAsync('library.update', params.get('identifier'), default_title = params.get('title', ''), on_complete = onComplete)
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


    def addView(self):

        params = getParams()

        movie_dict = self.add(params)

        return jsonified({
            'success': True,
            'added': True if movie_dict else False,
            'movie': movie_dict,
        })

    def edit(self):

        params = getParams()
        db = get_session()

        available_status = fireEvent('status.get', 'available', single = True)

        ids = splitString(params.get('id'))
        for movie_id in ids:

            m = db.query(Movie).filter_by(id = movie_id).first()
            if not m:
                continue

            m.profile_id = params.get('profile_id')

            # Remove releases
            for rel in m.releases:
                if rel.status_id is available_status.get('id'):
                    db.delete(rel)
                    db.commit()

            # Default title
            if params.get('default_title'):
                for title in m.library.titles:
                    title.default = toUnicode(params.get('default_title', '')).lower() == toUnicode(title.title).lower()

            db.commit()

            fireEvent('movie.restatus', m.id)

            movie_dict = m.to_dict(self.default_dict)
            fireEventAsync('searcher.single', movie_dict, on_complete = self.createNotifyFront(movie_id))

        db.expire_all()
        return jsonified({
            'success': True,
        })

    def deleteView(self):

        params = getParams()

        ids = splitString(params.get('id'))
        for movie_id in ids:
            self.delete(movie_id, delete_from = params.get('delete_from', 'all'))

        return jsonified({
            'success': True,
        })

    def delete(self, movie_id, delete_from = None):

        db = get_session()

        movie = db.query(Movie).filter_by(id = movie_id).first()
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
                    if delete_from in ['wanted', 'snatched']:
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

        m = db.query(Movie).filter_by(id = movie_id).first()
        if not m or len(m.library.titles) == 0:
            log.debug('Can\'t restatus movie, doesn\'t seem to exist.')
            return False

        log.debug('Changing status for %s', (m.library.titles[0].title))
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
            movie = db.query(Movie).filter_by(id = movie_id).first()
            fireEventAsync('searcher.single', movie.to_dict(self.default_dict), on_complete = self.createNotifyFront(movie_id))
            db.expire_all()

        return onComplete


    def createNotifyFront(self, movie_id):

        def notifyFront():
            db = get_session()
            movie = db.query(Movie).filter_by(id = movie_id).first()
            fireEvent('notify.frontend', type = 'movie.update.%s' % movie.id, data = movie.to_dict(self.default_dict))
            db.expire_all()

        return notifyFront

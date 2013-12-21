from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie import MovieTypeBase
from couchpotato.core.settings.model import Media
import time

log = CPLog(__name__)


class MovieBase(MovieTypeBase):

    _type = 'movie'

    def __init__(self):

        # Initialize this type
        super(MovieBase, self).__init__()
        self.initType()

        addApiView('movie.add', self.addView, docs = {
            'desc': 'Add new movie to the wanted list',
            'params': {
                'identifier': {'desc': 'IMDB id of the movie your want to add.'},
                'profile_id': {'desc': 'ID of quality profile you want the add the movie in. If empty will use the default profile.'},
                'category_id': {'desc': 'ID of category you want the add the movie in. If empty will use no category.'},
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

        addEvent('movie.add', self.add)

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
            m.category_id = tryInt(cat_id) if cat_id is not None and tryInt(cat_id) > 0 else (m.category_id or None)
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
        add_dict = self.add(params = kwargs)

        return {
            'success': True if add_dict else False,
            'movie': add_dict,
        }

    def edit(self, id = '', **kwargs):

        db = get_session()

        available_status = fireEvent('status.get', 'available', single = True)

        ids = splitString(id)
        for media_id in ids:

            m = db.query(Media).filter_by(id = media_id).first()
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

            fireEvent('media.restatus', m.id)

            movie_dict = m.to_dict(self.default_dict)
            fireEventAsync('movie.searcher.single', movie_dict, on_complete = self.createNotifyFront(media_id))

        db.expire_all()
        return {
            'success': True,
        }

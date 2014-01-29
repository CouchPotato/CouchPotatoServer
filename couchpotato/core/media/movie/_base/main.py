import traceback
from couchpotato import get_session, get_db
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import splitString, tryInt, getTitle
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
                'category_id': {'desc': 'ID of category you want the add the movie in. If empty will use no category.'},
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

        # library = fireEvent('library.add.movie', single = True, attrs = params, update_after = update_library)
        info = fireEvent('movie.info', merge = True, extended = False, identifier = params.get('identifier'))

        default_profile = fireEvent('profile.default', single = True)
        cat_id = params.get('category_id')

        try:
            db = get_db()

            new = False
            try:
                m = db.get('movie', params.get('identifier'), with_doc = True)['doc']
            except:
                new = True
                m = db.insert({
                    'type': 'movie',
                    'identifier': params.get('identifier'),
                    'status': status_id if status_id else 'active',
                    'profile_id': params.get('profile_id', default_profile.get('id')),
                    'category_id': tryInt(cat_id) if cat_id is not None and tryInt(cat_id) > 0 else None,
                })

            added = True
            do_search = False
            search_after = search_after and self.conf('search_on_add', section = 'moviesearcher')
            if new:
                onComplete = None
                if search_after:
                    onComplete = self.createOnComplete(m['_id'])

                # fireEventAsync('library.update.movie', params.get('identifier'), default_title = params.get('title', ''), on_complete = onComplete)
                search_after = False
            elif force_readd:

                # Clean snatched history
                for release in db.run('release', 'for_media', m['_id']):
                    if release.get('status') in ['downloaded', 'snatched', 'done']:
                        if params.get('ignore_previous', False):
                            release['status'] = 'ignored'
                            db.update(release)
                        else:
                            fireEvent('release.delete', release['_id'], single = True)

                m['profile_id'] = params.get('profile_id', default_profile.get('id'))
                m['category_id'] = tryInt(cat_id) if cat_id is not None and tryInt(cat_id) > 0 else (m['category_id'] or None)
            else:
                log.debug('Movie already exists, not updating: %s', params)
                added = False

            if force_readd:
                m['status'] = status_id if status_id else 'active'
                m['last_edit'] = int(time.time())
                do_search = True

            db.update(m)

            # Remove releases
            for rel in db.run('release', 'for_media', m['_id']):
                if rel['status'] is 'available':
                    db.delete(rel)

            movie_dict = db.run('movie', 'to_dict', m['_id'])

            if do_search and search_after:
                onComplete = self.createOnComplete(m['_id'])
                onComplete()

            if added:
                if params.get('title'):
                    message = 'Successfully added "%s" to your wanted list.' % params.get('title', '')
                else:
                    title = getTitle(m)
                    if title:
                        message = 'Successfully added "%s" to your wanted list.' % title
                    else:
                        message = 'Succesfully added to your wanted list.'
                fireEvent('notify.frontend', type = 'movie.added', data = movie_dict, message = message)

            return movie_dict
        except:
            log.error('Failed adding media: %s', traceback.format_exc())

    def addView(self, **kwargs):
        add_dict = self.add(params = kwargs)

        return {
            'success': True if add_dict else False,
            'movie': add_dict,
        }

    def edit(self, id = '', **kwargs):

        try:
            db = get_db()

            ids = splitString(id)
            for media_id in ids:

                try:
                    m = db.get('media', media_id)
                    m['profile_id'] = kwargs.get('profile_id')

                    cat_id = kwargs.get('category_id')
                    if cat_id is not None:
                        m['category_id'] = tryInt(cat_id) if tryInt(cat_id) > 0 else None

                    # Remove releases
                    for rel in db.run('release', 'for_media', m['_id']):
                        if rel['status'] is 'available':
                            db.delete(rel)

                    # Default title
                    if kwargs.get('default_title'):
                        for title in m['titles']:
                            title.default = toUnicode(kwargs.get('default_title', '')).lower() == toUnicode(title.title).lower()

                    db.update(m)

                    fireEvent('media.restatus', m['_id'])

                    movie_dict = db.run('media', 'to_dict', m['_id'])
                    fireEventAsync('movie.searcher.single', movie_dict, on_complete = self.createNotifyFront(media_id))

                except:
                    log.error('Can\'t edit non-existing media')

            return {
                'success': True,
            }
        except:
            log.error('Failed editing media: %s', traceback.format_exc())

        return {
            'success': False,
        }

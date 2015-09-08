import traceback
import time

from CodernityDB.database import RecordNotFound
from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import splitString, getTitle, getImdb, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie import MovieTypeBase
import six


log = CPLog(__name__)


class MovieBase(MovieTypeBase):

    _type = 'movie'

    def __init__(self):

        # Initialize this type
        super(MovieBase, self).__init__()
        self.initType()

        addApiView('movie.add', self.addView, docs = {
            'desc': 'Add new movie to the wanted list',
            'return': {'type': 'object', 'example': """{
    'success': True,
    'movie': object
}"""},
            'params': {
                'identifier': {'desc': 'IMDB id of the movie your want to add.'},
                'profile_id': {'desc': 'ID of quality profile you want the add the movie in. If empty will use the default profile.'},
                'force_readd': {'desc': 'Force re-add even if movie already in wanted or manage. Default: True'},
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
        addEvent('movie.update', self.update)
        addEvent('movie.update_release_dates', self.updateReleaseDate)

    def add(self, params = None, force_readd = True, search_after = True, update_after = True, notify_after = True, status = None):
        if not params: params = {}

        # Make sure it's a correct zero filled imdb id
        params['identifier'] = getImdb(params.get('identifier', ''))

        if not params.get('identifier'):
            msg = 'Can\'t add movie without imdb identifier.'
            log.error(msg)
            fireEvent('notify.frontend', type = 'movie.is_tvshow', message = msg)
            return False
        elif not params.get('info'):
            try:
                is_movie = fireEvent('movie.is_movie', identifier = params.get('identifier'), adding = True, single = True)
                if not is_movie:
                    msg = 'Can\'t add movie, seems to be a TV show.'
                    log.error(msg)
                    fireEvent('notify.frontend', type = 'movie.is_tvshow', message = msg)
                    return False
            except:
                pass

        info = params.get('info')
        if not info or (info and len(info.get('titles', [])) == 0):
            info = fireEvent('movie.info', merge = True, extended = False, identifier = params.get('identifier'))

        # Allow force re-add overwrite from param
        if 'force_readd' in params:
            fra = params.get('force_readd')
            force_readd = fra.lower() not in ['0', '-1'] if not isinstance(fra, bool) else fra

        # Set default title
        def_title = self.getDefaultTitle(info)

        # Default profile and category
        default_profile = {}
        if (not params.get('profile_id') and status != 'done') or params.get('ignore_previous', False):
            default_profile = fireEvent('profile.default', single = True)
        cat_id = params.get('category_id')

        try:
            db = get_db()

            media = {
                '_t': 'media',
                'type': 'movie',
                'title': def_title,
                'identifiers': {
                    'imdb': params.get('identifier')
                },
                'status': status if status else 'active',
                'profile_id': params.get('profile_id') or default_profile.get('_id'),
                'category_id': cat_id if cat_id is not None and len(cat_id) > 0 and cat_id != '-1' else None,
            }

            # Update movie info
            try: del info['in_wanted']
            except: pass
            try: del info['in_library']
            except: pass
            media['info'] = info

            new = False
            previous_profile = None
            try:
                m = db.get('media', 'imdb-%s' % params.get('identifier'), with_doc = True)['doc']

                try:
                    db.get('id', m.get('profile_id'))
                    previous_profile = m.get('profile_id')
                except RecordNotFound:
                    pass
                except:
                    log.error('Failed getting previous profile: %s', traceback.format_exc())
            except:
                new = True
                m = db.insert(media)

            # Update dict to be usable
            m.update(media)

            added = True
            do_search = False
            search_after = search_after and self.conf('search_on_add', section = 'moviesearcher')
            onComplete = None

            if new:
                if search_after:
                    onComplete = self.createOnComplete(m['_id'])
                search_after = False
            elif force_readd:

                # Clean snatched history
                for release in fireEvent('release.for_media', m['_id'], single = True):
                    if release.get('status') in ['downloaded', 'snatched', 'seeding', 'done']:
                        if params.get('ignore_previous', False):
                            fireEvent('release.update_status', release['_id'], status = 'ignored')
                        else:
                            fireEvent('release.delete', release['_id'], single = True)

                m['profile_id'] = (params.get('profile_id') or default_profile.get('_id')) if not previous_profile else previous_profile
                m['category_id'] = cat_id if cat_id is not None and len(cat_id) > 0 else (m.get('category_id') or None)
                m['last_edit'] = int(time.time())
                m['tags'] = []

                do_search = True
                db.update(m)
            else:
                try: del params['info']
                except: pass
                log.debug('Movie already exists, not updating: %s', params)
                added = False

            # Trigger update info
            if added and update_after:
                # Do full update to get images etc
                fireEventAsync('movie.update', m['_id'], default_title = params.get('title'), on_complete = onComplete)

            # Remove releases
            for rel in fireEvent('release.for_media', m['_id'], single = True):
                if rel['status'] is 'available':
                    db.delete(rel)

            movie_dict = fireEvent('media.get', m['_id'], single = True)
            if not movie_dict:
                log.debug('Failed adding media, can\'t find it anymore')
                return False

            if do_search and search_after:
                onComplete = self.createOnComplete(m['_id'])
                onComplete()

            if added and notify_after:

                if params.get('title'):
                    message = 'Successfully added "%s" to your wanted list.' % params.get('title', '')
                else:
                    title = getTitle(m)
                    if title:
                        message = 'Successfully added "%s" to your wanted list.' % title
                    else:
                        message = 'Successfully added to your wanted list.'
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
                    m = db.get('id', media_id)
                    m['profile_id'] = kwargs.get('profile_id') or m['profile_id']

                    cat_id = kwargs.get('category_id')
                    if cat_id is not None:
                        m['category_id'] = cat_id if len(cat_id) > 0 else m['category_id']

                    # Remove releases
                    for rel in fireEvent('release.for_media', m['_id'], single = True):
                        if rel['status'] is 'available':
                            db.delete(rel)

                    # Default title
                    if kwargs.get('default_title'):
                        m['title'] = kwargs.get('default_title')

                    db.update(m)

                    fireEvent('media.restatus', m['_id'], single = True)

                    m = db.get('id', media_id)

                    movie_dict = fireEvent('media.get', m['_id'], single = True)
                    fireEventAsync('movie.searcher.single', movie_dict, on_complete = self.createNotifyFront(media_id))

                except:
                    print traceback.format_exc()
                    log.error('Can\'t edit non-existing media')

            return {
                'success': True,
            }
        except:
            log.error('Failed editing media: %s', traceback.format_exc())

        return {
            'success': False,
        }

    def update(self, media_id = None, identifier = None, default_title = None, extended = False):
        """
        Update movie information inside media['doc']['info']

        @param media_id: document id
        @param default_title: default title, if empty, use first one or existing one
        @param extended: update with extended info (parses more info, actors, images from some info providers)
        @return: dict, with media
        """

        if self.shuttingDown():
            return

        lock_key = 'media.get.%s' % media_id if media_id else identifier
        self.acquireLock(lock_key)

        media = {}
        try:
            db = get_db()

            if media_id:
                media = db.get('id', media_id)
            else:
                media = db.get('media', 'imdb-%s' % identifier, with_doc = True)['doc']

            info = fireEvent('movie.info', merge = True, extended = extended, identifier = getIdentifier(media))

            # Don't need those here
            try: del info['in_wanted']
            except: pass
            try: del info['in_library']
            except: pass

            if not info or len(info) == 0:
                log.error('Could not update, no movie info to work with: %s', identifier)
                return False

            # Update basic info
            media['info'] = info

            titles = info.get('titles', [])
            log.debug('Adding titles: %s', titles)

            # Define default title
            if default_title or media.get('title') == 'UNKNOWN' or len(media.get('title', '')) == 0:
                media['title'] = self.getDefaultTitle(info, default_title)

            # Files
            image_urls = info.get('images', [])

            self.getPoster(media, image_urls)

            db.update(media)
        except:
            log.error('Failed update media: %s', traceback.format_exc())

        self.releaseLock(lock_key)
        return media

    def updateReleaseDate(self, media_id):
        """
        Update release_date (eta) info only

        @param media_id: document id
        @return: dict, with dates dvd, theater, bluray, expires
        """

        try:
            db = get_db()

            media = db.get('id', media_id)

            if not media.get('info'):
                media = self.update(media_id)
                dates = media.get('info', {}).get('release_date')
            else:
                dates = media.get('info').get('release_date')

            if dates and (dates.get('expires', 0) < time.time() or dates.get('expires', 0) > time.time() + (604800 * 4)) or not dates:
                dates = fireEvent('movie.info.release_date', identifier = getIdentifier(media), merge = True)
                media['info'].update({'release_date': dates})
                db.update(media)

            return dates
        except:
            log.error('Failed updating release dates: %s', traceback.format_exc())

        return {}

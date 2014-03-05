import traceback
from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import splitString, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie import MovieTypeBase
import time
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
        addEvent('movie.update_info', self.updateInfo)
        addEvent('movie.update_release_dates', self.updateReleaseDate)

    def add(self, params = None, force_readd = True, search_after = True, update_after = True, notify_after = True, status = None):
        if not params: params = {}

        if not params.get('identifier'):
            msg = 'Can\'t add movie without imdb identifier.'
            log.error(msg)
            fireEvent('notify.frontend', type = 'movie.is_tvshow', message = msg)
            return False
        elif not params.get('info'):
            try:
                is_movie = fireEvent('movie.is_movie', identifier = params.get('identifier'), single = True)
                if not is_movie:
                    msg = 'Can\'t add movie, seems to be a TV show.'
                    log.error(msg)
                    fireEvent('notify.frontend', type = 'movie.is_tvshow', message = msg)
                    return False
            except:
                pass

        info = params.get('info')
        if not info:
            info = fireEvent('movie.info', merge = True, extended = False, identifier = params.get('identifier'))

        # Set default title
        default_title = toUnicode(info.get('title'))
        titles = info.get('titles', [])
        counter = 0
        def_title = None
        for title in titles:
            if (len(default_title) == 0 and counter == 0) or len(titles) == 1 or title.lower() == toUnicode(default_title.lower()) or (toUnicode(default_title) == six.u('') and toUnicode(titles[0]) == title):
                def_title = toUnicode(title)
                break
            counter += 1

        if not def_title:
            def_title = toUnicode(titles[0])

        # Default profile and category
        default_profile = fireEvent('profile.default', single = True)
        cat_id = params.get('category_id')

        try:
            db = get_db()

            media = {
                '_t': 'media',
                'type': 'movie',
                'title': def_title,
                'identifier': params.get('identifier'),
                'status': status if status else 'active',
                'profile_id': params.get('profile_id', default_profile.get('_id')),
                'category_id': cat_id if cat_id is not None and len(cat_id) > 0 else None,
            }

            new = False
            try:
                m = db.get('media', params.get('identifier'), with_doc = True)['doc']
            except:
                new = True
                m = db.insert(media)

            # Update dict to be usable
            m.update(media)

            # Update movie info
            try: del info['in_wanted']
            except: pass
            try: del info['in_library']
            except: pass
            m['info'] = info

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
                for release in db.run('release', 'for_media', m['_id']):
                    if release.get('status') in ['downloaded', 'snatched', 'done']:
                        if params.get('ignore_previous', False):
                            release['status'] = 'ignored'
                            db.update(release)
                        else:
                            fireEvent('release.delete', release['_id'], single = True)

                m['profile_id'] = params.get('profile_id', default_profile.get('id'))
                m['category_id'] = cat_id if cat_id is not None and len(cat_id) > 0 else (m.get('category_id') or None)
            else:
                log.debug('Movie already exists, not updating: %s', params)
                added = False

            if force_readd:
                m['last_edit'] = int(time.time())
                do_search = True

            if added:
                db.update(m)

                # Do full update to get images etc
                if update_after:
                    fireEventAsync('movie.update_info', m['_id'], default_title = params.get('title'), on_complete = onComplete)

            # Remove releases
            for rel in db.run('release', 'for_media', m['_id']):
                if rel['status'] is 'available':
                    db.delete(rel)

            movie_dict = db.run('media', 'to_dict', m['_id'])

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
                    m['profile_id'] = kwargs.get('profile_id')

                    cat_id = kwargs.get('category_id')
                    if cat_id is not None:
                        m['category_id'] = cat_id if len(cat_id) > 0 else None

                    # Remove releases
                    for rel in db.run('release', 'for_media', m['_id']):
                        if rel['status'] is 'available':
                            db.delete(rel)

                    # Default title
                    if kwargs.get('default_title'):
                        m['title'] = kwargs.get('default_title')

                    db.update(m)

                    fireEvent('media.restatus', m['_id'])

                    m = db.get('id', media_id)

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

    def updateInfo(self, media_id = None, identifier = None, default_title = None, extended = False):
        """
        Update movie information inside media['doc']['info']

        @param media_id: document id
        @param default_title: default title, if empty, use first one or existing one
        @param extended: update with extended info (parses more info, actors, images from some info providers)
        @return: dict, with media
        """

        if self.shuttingDown():
            return

        try:
            db = get_db()

            if media_id:
                media = db.get('id', media_id)
            else:
                media = db.get('media', identifier, with_doc = True)['doc']

            info = fireEvent('movie.info', merge = True, extended = extended, identifier = media.get('identifier'))

            # Don't need those here
            try: del info['in_wanted']
            except: pass
            try: del info['in_library']
            except: pass

            if not info or len(info) == 0:
                log.error('Could not update, no movie info to work with: %s', media.get('identifier'))
                return False

            # Update basic info
            media['info'] = info

            titles = info.get('titles', [])
            log.debug('Adding titles: %s', titles)

            # Define default title
            def_title = None
            if default_title:
                counter = 0
                for title in titles:
                    if title.lower() == toUnicode(default_title.lower()) or (toUnicode(default_title) == six.u('') and toUnicode(titles[0]) == title):
                        def_title = toUnicode(title)
                        break
                    counter += 1

            if not def_title:
                def_title = toUnicode(titles[0])

            media['title'] = def_title

            # Files
            images = info.get('images', [])
            media['files'] = media.get('files', {})
            for image_type in ['poster']:
                for image in images.get(image_type, []):
                    if not isinstance(image, (str, unicode)):
                        continue

                    file_type = 'image_%s' % image_type
                    if file_type not in media['files']:
                        file_path = fireEvent('file.download', url = image, single = True)
                        media['files']['image_%s' % image_type] = [file_path];

                    break

            db.update(media)

            return media
        except:
            log.error('Failed update media: %s', traceback.format_exc())

        return {}

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
                media = self.updateInfo(media_id)
                dates = media.get('info', {}).get('release_date')
            else:
                dates = media.get('info').get('release_date')

            if dates and (dates.get('expires', 0) < time.time() or dates.get('expires', 0) > time.time() + (604800 * 4)) or not dates:
                dates = fireEvent('movie.info.release_date', identifier = media['identifier'], merge = True)
                media['info'].update({'release_date': dates})
                db.update(media)

            return dates
        except:
            log.error('Failed updating release dates: %s', traceback.format_exc())

        return {}

    def simplifyTitle(self, title):
        """
        Removes all special chars from a title so it's easier to make sortable
        @param title: media title
        @return: string, simplified title
        """

        title = toUnicode(title)

        nr_prefix = '' if title[0] in ascii_letters else '#'
        title = simplifyString(title)

        for prefix in ['the ']:
            if prefix == title[:len(prefix)]:
                title = title[len(prefix):]
                break

        return nr_prefix + title

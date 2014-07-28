import time
import traceback

from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import getTitle, find
from couchpotato.core.logger import CPLog
from couchpotato.core.media import MediaBase
from qcond import QueryCondenser


log = CPLog(__name__)


class ShowBase(MediaBase):

    _type = 'show'

    def __init__(self):
        super(ShowBase, self).__init__()

        addApiView('show.add', self.addView, docs = {
            'desc': 'Add new show to the wanted list',
            'params': {
                'identifier': {'desc': 'IMDB id of the show your want to add.'},
                'profile_id': {'desc': 'ID of quality profile you want the add the show in. If empty will use the default profile.'},
                'category_id': {'desc': 'ID of category you want the add the show in.'},
                'title': {'desc': 'Title of the show to use for search and renaming'},
            }
        })

        addEvent('show.add', self.add)
        addEvent('show.update_info', self.updateInfo)

    def addView(self, **kwargs):
        add_dict = self.add(params = kwargs)

        return {
            'success': True if add_dict else False,
            'show': add_dict,
        }

    def add(self, params = None, force_readd = True, search_after = True, update_after = True, notify_after = True, status = None):
        if not params: params = {}

        db = get_db()

        # Identifiers
        if not params.get('identifiers'):
            msg = 'Can\'t add show without at least 1 identifier.'
            log.error(msg)
            fireEvent('notify.frontend', type = 'show.no_identifier', message = msg)
            return False

        info = params.get('info')
        if not info or (info and len(info.get('titles', [])) == 0):
            info = fireEvent('show.info', merge = True, identifiers = params.get('identifiers'))

        # Set default title
        def_title = self.getDefaultTitle(info)

        # Default profile and category
        default_profile = {}
        if not params.get('profile_id'):
            default_profile = fireEvent('profile.default', single = True)
        cat_id = params.get('category_id')

        # Add Show
        try:
            media = {
                '_t': 'media',
                'type': 'show',
                'title': def_title,
                'identifiers': info.get('identifiers'),
                'status': status if status else 'active',
                'profile_id': params.get('profile_id', default_profile.get('_id')),
                'category_id': cat_id if cat_id is not None and len(cat_id) > 0 and cat_id != '-1' else None
            }

            # Remove season info for later use (save separately)
            seasons_info = info.get('seasons', {})
            identifiers = info.get('identifiers', {})

            # Make sure we don't nest in_wanted data
            try: del info['identifiers']
            except: pass
            try: del info['in_wanted']
            except: pass
            try: del info['in_library']
            except: pass
            try: del info['identifiers']
            except: pass
            try: del info['seasons']
            except: pass

            media['info'] = info

            new = False
            try:
                m = fireEvent('media.with_identifiers', params.get('identifiers'), with_doc = True, single = True)['doc']
            except:
                new = True
                m = db.insert(media)

            # Update dict to be usable
            m.update(media)


            added = True
            do_search = False
            search_after = search_after and self.conf('search_on_add', section = 'showsearcher')
            onComplete = None

            if new:
                if search_after:
                    onComplete = self.createOnComplete(m['_id'])
                search_after = False
            elif force_readd:

                # Clean snatched history
                for release in fireEvent('release.for_media', m['_id'], single = True):
                    if release.get('status') in ['downloaded', 'snatched', 'done']:
                        if params.get('ignore_previous', False):
                            release['status'] = 'ignored'
                            db.update(release)
                        else:
                            fireEvent('release.delete', release['_id'], single = True)

                m['profile_id'] = params.get('profile_id', default_profile.get('id'))
                m['category_id'] = media.get('category_id')
                m['last_edit'] = int(time.time())

                do_search = True
                db.update(m)
            else:
                try: del params['info']
                except: pass
                log.debug('Show already exists, not updating: %s', params)
                added = False

            # Trigger update info
            if added and update_after:
                # Do full update to get images etc
                fireEventAsync('show.update_info', m['_id'], info = info, on_complete = onComplete)

            # Remove releases
            for rel in fireEvent('release.for_media', m['_id'], single = True):
                if rel['status'] is 'available':
                    db.delete(rel)

            movie_dict = fireEvent('media.get', m['_id'], single = True)

            if do_search and search_after:
                onComplete = self.createOnComplete(m['_id'])
                onComplete()

            # Add Seasons
            for season_nr in seasons_info:

                season_info = seasons_info[season_nr]
                episodes = season_info.get('episodes', {})

                season = fireEvent('show.season.add', m.get('_id'), season_info, update_after = False, single = True)

                # Add Episodes
                for episode_nr in episodes:

                    episode_info = episodes[episode_nr]
                    episode_info['season_number'] = season_nr
                    fireEvent('show.episode.add', season.get('_id'), episode_info, update_after = False, single = True)

            if added and notify_after:

                if params.get('title'):
                    message = 'Successfully added "%s" to your wanted list.' % params.get('title', '')
                else:
                    title = getTitle(m)
                    if title:
                        message = 'Successfully added "%s" to your wanted list.' % title
                    else:
                        message = 'Successfully added to your wanted list.'
                fireEvent('notify.frontend', type = 'show.added', data = movie_dict, message = message)


            return movie_dict
        except:
            log.error('Failed adding media: %s', traceback.format_exc())

    def updateInfo(self, media_id = None, media = None, identifiers = None, info = None):
        """
        Update movie information inside media['doc']['info']

        @param media_id: document id
        @param identifiers: identifiers from multiple providers
            {
                'thetvdb': 123,
                'imdb': 'tt123123',
                ..
            }
        @param extended: update with extended info (parses more info, actors, images from some info providers)
        @return: dict, with media
        """

        if not info: info = {}
        if not identifiers: identifiers = {}

        if self.shuttingDown():
            return

        try:
            db = get_db()

            if media is None:
                if media_id:
                    media = db.get('id', media_id)
                else:
                    media = db.get('media', identifiers, with_doc = True)['doc']

            if not info:
                info = fireEvent('show.info', identifiers = media.get('identifiers'), merge = True)

            # Remove season info for later use (save separately)
            seasons_info = info.get('seasons', {})
            identifiers = info.get('identifiers', {})

            try: del info['identifiers']
            except: pass
            try: del info['in_wanted']
            except: pass
            try: del info['in_library']
            except: pass
            try: del info['identifiers']
            except: pass
            try: del info['seasons']
            except: pass

            if not info or len(info) == 0:
                log.error('Could not update, no show info to work with: %s', media.get('identifier'))
                return False

            # Update basic info
            media['info'] = info

            show_tree = fireEvent('library.tree', media_id = media['_id'], single = True)

            # Update seasons
            for season_num in seasons_info:
                season_info = seasons_info[season_num]
                episodes = season_info.get('episodes', {})

                # Find season that matches number
                season = find(lambda s: s.get('info', {}).get('number', 0) == season_num, show_tree.get('seasons', []))

                if not season:
                    log.warning('Unable to find season "%s"', season_num)
                    continue

                # Update season
                fireEvent('show.season.update_info', season['_id'], info = season_info, single = True)

                # Update episodes
                for episode_num in episodes:
                    episode_info = episodes[episode_num]
                    episode_info['season_number'] = season_num

                    # Find episode that matches number
                    episode = find(lambda s: s.get('info', {}).get('number', 0) == episode_num, season.get('episodes', []))

                    fireEvent('show.episode.update_info', episode['_id'], info = episode_info, single = True)

            # Update image file
            image_urls = info.get('images', [])
            self.getPoster(media, image_urls)

            db.update(media)
            return media
        except:
            log.error('Failed update media: %s', traceback.format_exc())

        return {}

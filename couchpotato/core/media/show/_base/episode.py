from couchpotato import get_db
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.media import MediaBase


log = CPLog(__name__)

autoload = 'Episode'


class Episode(MediaBase):

    def __init__(self):
        addEvent('show.episode.add', self.add)
        addEvent('show.episode.update', self.update)
        addEvent('show.episode.update_extras', self.updateExtras)

    def add(self, parent_id, info = None, update_after = True, status = None):
        if not info: info = {}

        identifiers = info.pop('identifiers', None)

        if not identifiers:
            log.warning('Unable to add episode, missing identifiers (info provider mismatch?)')
            return

        # Add Season
        episode_info = {
            '_t': 'media',
            'type': 'show.episode',
            'identifiers': identifiers,
            'status': status if status else 'active',
            'parent_id': parent_id,
            'info': info, # Returned dict by providers
        }

        # Check if season already exists
        existing_episode = fireEvent('media.with_identifiers', identifiers, with_doc = True, single = True)

        db = get_db()

        if existing_episode:
            s = existing_episode['doc']
            s.update(episode_info)

            episode = db.update(s)
        else:
            episode = db.insert(episode_info)

        # Update library info
        if update_after is not False:
            handle = fireEventAsync if update_after is 'async' else fireEvent
            handle('show.episode.update_extras', episode, info, store = True, single = True)

        return episode

    def update(self, media_id = None, identifiers = None, info = None):
        if not info: info = {}

        if self.shuttingDown():
            return

        db = get_db()

        episode = db.get('id', media_id)

        # Get new info
        if not info:
            season = db.get('id', episode['parent_id'])
            show = db.get('id', season['parent_id'])

            info = fireEvent(
                'episode.info', show.get('identifiers'), {
                    'season_identifiers': season.get('identifiers'),
                    'season_number': season.get('info', {}).get('number'),

                    'episode_identifiers': episode.get('identifiers'),
                    'episode_number': episode.get('info', {}).get('number'),

                    'absolute_number': episode.get('info', {}).get('absolute_number')
                },
                merge = True
            )

            info['season_number'] = season.get('info', {}).get('number')

        identifiers = info.pop('identifiers', None) or identifiers

        # Update/create media
        episode['identifiers'].update(identifiers)
        episode.update({'info': info})

        self.updateExtras(episode, info)

        db.update(episode)
        return episode

    def updateExtras(self, episode, info, store=False):
        db = get_db()

        # Get images
        image_urls = info.get('images', [])
        existing_files = episode.get('files', {})
        self.getPoster(image_urls, existing_files)

        if store:
            db.update(episode)

from couchpotato import get_db
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.media import MediaBase


log = CPLog(__name__)

autoload = 'Episode'


class Episode(MediaBase):

    def __init__(self):
        addEvent('media.search_query', self.query)
        addEvent('media.identifier', self.identifier)

        addEvent('show.episode.add', self.add)
        addEvent('show.episode.update_info', self.updateInfo)

    def add(self, parent_id, info = None, update_after = True):
        if not info: info = {}

        identifiers = info.get('identifiers')
        try: del info['identifiers']
        except: pass

        # Add Season
        episode_info = {
            '_t': 'media',
            'type': 'episode',
            'identifiers': identifiers,
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
            handle('show.season.update_info', episode.get('_id'), info = info, single = True)

        return episode

    def updateInfo(self, media_id = None, info = None, force = False):
        if not info: info = {}

        if self.shuttingDown():
            return

        db = get_db()

        episode = db.get('id', media_id)

        # Get new info
        if not info:
            info = fireEvent('episode.info', episode.get('identifiers'), merge = True)

        # Update/create media
        if force:

            episode['identifiers'].update(info['identifiers'])
            if 'identifiers' in info:
                del info['identifiers']

            episode.update({'info': info})
            e = db.update(episode)
            episode.update(e)

        # Get images
        image_urls = info.get('images', [])
        existing_files = episode.get('files', {})
        self.getPoster(image_urls, existing_files)

        return episode

    def query(self, library, first = True, condense = True, include_identifier = True, **kwargs):
        if library is list or library.get('type') != 'episode':
            return

        # Get the titles of the season
        if not library.get('related_libraries', {}).get('season', []):
            log.warning('Invalid library, unable to determine title.')
            return

        titles = fireEvent(
            'media.search_query',
            library['related_libraries']['season'][0],
            first=False,
            include_identifier=include_identifier,
            condense=condense,

            single=True
        )

        identifier = fireEvent('media.identifier', library, single = True)

        # Add episode identifier to titles
        if include_identifier and identifier.get('episode'):
            titles = [title + ('E%02d' % identifier['episode']) for title in titles]


        if first:
            return titles[0] if titles else None

        return titles


    def identifier(self, media):
        if media.get('type') != 'episode':
            return

        identifier = {
            'season': None,
            'episode': None
        }

        scene_map = media['info'].get('map_episode', {}).get('scene')

        if scene_map:
            # Use scene mappings if they are available
            identifier['season'] = scene_map.get('season_nr')
            identifier['episode'] = scene_map.get('episode_nr')
        else:
            # Fallback to normal season/episode numbers
            identifier['season'] = media['info'].get('season_number')
            identifier['episode'] = media['info'].get('number')


        # Cast identifiers to integers
        # TODO this will need changing to support identifiers with trailing 'a', 'b' characters
        identifier['season'] = tryInt(identifier['season'], None)
        identifier['episode'] = tryInt(identifier['episode'], None)

        return identifier

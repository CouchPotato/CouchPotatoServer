from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.plugins.base import Plugin


log = CPLog(__name__)

autload = 'Episode'

class Episode(Plugin):

    def __init__(self):
        addEvent('media.search_query', self.query)
        addEvent('media.identifier', self.identifier)

        addEvent('show.episode.add', self.add)
        addEvent('show.episode.update_info', self.updateInfo)

    def add(self, parent_id, update_after = True):

        # Add Season
        season = {
            '_t': 'media',
            'type': 'episode',
            'nr': 1,
            'identifiers': {
                'imdb': 'tt1234',
                'thetvdb': 123,
                'tmdb': 123,
                'rage': 123
            },
            'parent': '_id',
            'info': {}, # Returned dict by providers
        }

        episode_exists = True or False

        if episode_exists:
            pass #update existing
        else:
            pass # Add Episode


        # Update library info
        if update_after is not False:
            handle = fireEventAsync if update_after is 'async' else fireEvent
            handle('show.episode.update_info', season.get('_id'), default_title = toUnicode(attrs.get('title', '')))

        return season

    def updateInfo(self, media_id = None, default_title = '', force = False):

        if self.shuttingDown():
            return

        # Get new info
        fireEvent('episode.info', merge = True)

        # Update/create media


        # Get images


        return info

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


    def identifier(self, library):
        if library.get('type') != 'episode':
            return

        identifier = {
            'season': None,
            'episode': None
        }

        scene_map = library['info'].get('map_episode', {}).get('scene')

        if scene_map:
            # Use scene mappings if they are available
            identifier['season'] = scene_map.get('season')
            identifier['episode'] = scene_map.get('episode')
        else:
            # Fallback to normal season/episode numbers
            identifier['season'] = library.get('season_number')
            identifier['episode'] = library.get('episode_number')


        # Cast identifiers to integers
        # TODO this will need changing to support identifiers with trailing 'a', 'b' characters
        identifier['season'] = tryInt(identifier['season'], None)
        identifier['episode'] = tryInt(identifier['episode'], None)

        return identifier

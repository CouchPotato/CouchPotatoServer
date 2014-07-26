from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.library.base import LibraryBase

log = CPLog(__name__)

autoload = 'EpisodeLibraryPlugin'


class EpisodeLibraryPlugin(LibraryBase):
    def __init__(self):
        addEvent('library.query', self.query)
        addEvent('library.identifier', self.identifier)

    def query(self, media, first = True, condense = True, include_identifier = True, **kwargs):
        if media.get('type') != 'show.episode':
            return

        related = fireEvent('library.related', media, single = True)

        # Get season titles
        titles = fireEvent(
            'library.query', related['season'],

            first = False,
            include_identifier = include_identifier,
            condense = condense,

            single = True
        )

        # Add episode identifier to titles
        if include_identifier:
            identifier = fireEvent('library.identifier', media, single = True)

            if identifier and identifier.get('episode'):
                titles = [title + ('E%02d' % identifier['episode']) for title in titles]

        if first:
            return titles[0] if titles else None

        return titles

    def identifier(self, media):
        if media.get('type') != 'show.episode':
            return

        identifier = {
            'season': None,
            'episode': None
        }

        # TODO identifier mapping
        # scene_map = media['info'].get('map_episode', {}).get('scene')

        # if scene_map:
        #     # Use scene mappings if they are available
        #     identifier['season'] = scene_map.get('season_nr')
        #     identifier['episode'] = scene_map.get('episode_nr')
        # else:
        # Fallback to normal season/episode numbers
        identifier['season'] = media['info'].get('season_number')
        identifier['episode'] = media['info'].get('number')

        # Cast identifiers to integers
        # TODO this will need changing to support identifiers with trailing 'a', 'b' characters
        identifier['season'] = tryInt(identifier['season'], None)
        identifier['episode'] = tryInt(identifier['episode'], None)

        return identifier

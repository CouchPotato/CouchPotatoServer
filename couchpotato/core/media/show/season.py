from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.plugins.base import Plugin


log = CPLog(__name__)

autload = 'Season'


class Season(Plugin):

    def __init__(self):
        addEvent('media.search_query', self.query)
        addEvent('media.identifier', self.identifier)

        addEvent('show.season.add', self.update)
        addEvent('show.season.update_info', self.update)

    def query(self, library, first = True, condense = True, include_identifier = True, **kwargs):
        if library is list or library.get('type') != 'season':
            return

        # Get the titles of the show
        if not library.get('related_libraries', {}).get('show', []):
            log.warning('Invalid library, unable to determine title.')
            return

        titles = fireEvent(
            'media._search_query',
            library['related_libraries']['show'][0],
            first=False,
            condense=condense,

            single=True
        )

        # Add season map_names if they exist
        if 'map_names' in library['info']:
            season_names = library['info']['map_names'].get(str(library['season_number']), {})

            # Add titles from all locations
            # TODO only add name maps from a specific location
            for location, names in season_names.items():
                titles += [name for name in names if name and name not in titles]


        identifier = fireEvent('media.identifier', library, single = True)

        # Add season identifier to titles
        if include_identifier and identifier.get('season') is not None:
            titles = [title + (' S%02d' % identifier['season']) for title in titles]


        if first:
            return titles[0] if titles else None

        return titles

    def identifier(self, library):
        if library.get('type') != 'season':
            return

        return {
            'season': tryInt(library['season_number'], None)
        }

    def add(self, parent_id, update_after = True):

        # Add Season
        season = {
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

        # Check if season already exists
        season_exists = True or False

        if season_exists:
            pass #update existing
        else:

            db.insert(season)


        # Update library info
        if update_after is not False:
            handle = fireEventAsync if update_after is 'async' else fireEvent
            handle('show.season.update_info', episode.get('_id'))

        return season

    def update_info(self, media_id = None, default_title = '', force = False):

        if self.shuttingDown():
            return

        # Get new info
        fireEvent('season.info', merge = True)

        # Update/create media

        # Get images


        return info

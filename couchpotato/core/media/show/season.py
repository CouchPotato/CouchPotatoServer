from couchpotato import get_db
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.media import MediaBase


log = CPLog(__name__)

autoload = 'Season'


class Season(MediaBase):

    def __init__(self):
        addEvent('media.search_query', self.query)
        addEvent('media.identifier', self.identifier)

        addEvent('show.season.add', self.add)
        addEvent('show.season.update_info', self.updateInfo)

    def add(self, parent_id, info = None, update_after = True):
        if not info: info = {}

        identifiers = info.get('identifiers')
        try: del info['identifiers']
        except: pass
        try: del info['episodes']
        except: pass

        # Add Season
        season_info = {
            '_t': 'media',
            'type': 'season',
            'identifiers': identifiers,
            'parent_id': parent_id,
            'info': info,  # Returned dict by providers
        }

        # Check if season already exists
        existing_season = fireEvent('media.with_identifiers', identifiers, with_doc = True, single = True)

        db = get_db()

        if existing_season:
            s = existing_season['doc']
            s.update(season_info)
            season = db.update(s)
        else:
            season = db.insert(season_info)

        # Update library info
        if update_after is not False:
            handle = fireEventAsync if update_after is 'async' else fireEvent
            handle('show.season.update_info', season.get('_id'), info = info, single = True)

        return season

    def updateInfo(self, media_id = None, info = None, force = False):
        if not info: info = {}

        if self.shuttingDown():
            return

        db = get_db()

        season = db.get('id', media_id)

        # Get new info
        if not info:
            info = fireEvent('season.info', season.get('identifiers'), merge = True)

        # Update/create media
        if force:

            season['identifiers'].update(info['identifiers'])
            if 'identifiers' in info:
                del info['identifiers']

            season.update({'info': info})
            s = db.update(season)
            season.update(s)

        # Get images
        image_urls = info.get('images', [])
        existing_files = season.get('files', {})
        self.getPoster(image_urls, existing_files)

        return season

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

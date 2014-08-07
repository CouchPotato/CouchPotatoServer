from couchpotato import get_db
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.media import MediaBase


log = CPLog(__name__)

autoload = 'Season'


class Season(MediaBase):

    def __init__(self):
        addEvent('show.season.add', self.add)
        addEvent('show.season.update', self.update)
        addEvent('show.season.update_extras', self.updateExtras)

    def add(self, parent_id, info = None, update_after = True, status = None):
        if not info: info = {}

        identifiers = info.pop('identifiers', None)
        info.pop('episodes', None)

        # Add Season
        season_info = {
            '_t': 'media',
            'type': 'show.season',
            'identifiers': identifiers,
            'status': status if status else 'active',
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
            handle('show.season.update_extras', season, info, store = True, single = True)

        return season

    def update(self, media_id = None, identifiers = None, info = None):
        if not info: info = {}

        if self.shuttingDown():
            return

        db = get_db()

        season = db.get('id', media_id)
        show = db.get('id', season['parent_id'])

        # Get new info
        if not info:
            info = fireEvent('season.info', show.get('identifiers'), {
                'season_number': season.get('info', {}).get('number', 0)
            }, merge = True)

        identifiers = info.pop('identifiers', None) or identifiers
        info.pop('episodes', None)

        # Update/create media
        season['identifiers'].update(identifiers)
        season.update({'info': info})

        self.updateExtras(season, info)

        db.update(season)
        return season

    def updateExtras(self, season, info, store=False):
        db = get_db()

        # Get images
        image_urls = info.get('images', [])
        existing_files = season.get('files', {})
        self.getPoster(image_urls, existing_files)

        if store:
            db.update(season)

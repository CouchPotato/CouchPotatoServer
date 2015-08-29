import random as rndm
import time
from CodernityDB.database import RecordDeleted, RecordNotFound

from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin


log = CPLog(__name__)

autoload = 'Dashboard'


class Dashboard(Plugin):

    def __init__(self):
        addApiView('dashboard.soon', self.getSoonView)

    def getSoonView(self, limit_offset = None, random = False, late = False, **kwargs):

        db = get_db()
        now = time.time()

        # Get profiles first, determine pre or post theater
        profiles = fireEvent('profile.all', single = True)
        pre_releases = fireEvent('quality.pre_releases', single = True)

        # See what the profile contain and cache it
        profile_pre = {}
        for profile in profiles:
            contains = {}
            for q_identifier in profile.get('qualities', []):
                contains['theater' if q_identifier in pre_releases else 'dvd'] = True

            profile_pre[profile.get('_id')] = contains

        # Add limit
        limit = 12
        if limit_offset:
            splt = splitString(limit_offset) if isinstance(limit_offset, (str, unicode)) else limit_offset
            limit = tryInt(splt[0])

        # Get all active medias
        active_ids = [x['_id'] for x in fireEvent('media.with_status', 'active', with_doc = False, single = True)]

        medias = []

        if len(active_ids) > 0:

            # Order by title or randomize
            if not random:
                orders_ids = db.all('media_title')
                active_ids = [x['_id'] for x in orders_ids if x['_id'] in active_ids]
            else:
                rndm.shuffle(active_ids)

            for media_id in active_ids:
                try:
                    media = db.get('id', media_id)
                except RecordDeleted:
                    log.debug('Record already deleted: %s', media_id)
                    continue

                except RecordNotFound:
                    log.debug('Record not found: %s', media_id)
                    continue

                pp = profile_pre.get(media.get('profile_id'))
                if not pp: continue

                eta = media['info'].get('release_date', {}) or {}
                coming_soon = False

                # Theater quality
                if pp.get('theater') and fireEvent('movie.searcher.could_be_released', True, eta, media['info']['year'], single = True):
                    coming_soon = 'theater'
                elif pp.get('dvd') and fireEvent('movie.searcher.could_be_released', False, eta, media['info']['year'], single = True):
                    coming_soon = 'dvd'

                if coming_soon:

                    # Don't list older movies
                    eta_date = eta.get(coming_soon)
                    eta_3month_passed = eta_date < (now - 7862400)  # Release was more than 3 months ago

                    if (not late and not eta_3month_passed) or \
                            (late and eta_3month_passed):

                        add = True

                        # Check if it doesn't have any releases
                        if late:
                            media['releases'] = fireEvent('release.for_media', media['_id'], single = True)

                            for release in media.get('releases', []):
                                if release.get('status') in ['snatched', 'available', 'seeding', 'downloaded']:
                                    add = False
                                    break

                        if add:
                            medias.append(media)

                        if len(medias) >= limit:
                            break

        return {
            'success': True,
            'empty': len(medias) == 0,
            'movies': medias,
        }

    getLateView = getSoonView

from datetime import date
import random as rndm
import time

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
        now_year = date.today().year

        if len(active_ids) > 0:

            # Order by title or randomize
            if not random:
                orders_ids = db.all('media_title')
                active_ids = [x['_id'] for x in orders_ids if x['_id'] in active_ids]
            else:
                rndm.shuffle(active_ids)

            for media_id in active_ids:
                media = db.get('id', media_id)

                pp = profile_pre.get(media['profile_id'])
                if not pp: continue

                eta = media['info'].get('release_date', {}) or {}
                coming_soon = False

                # Theater quality
                if pp.get('theater') and fireEvent('movie.searcher.could_be_released', True, eta, media['info']['year'], single = True):
                    coming_soon = True
                elif pp.get('dvd') and fireEvent('movie.searcher.could_be_released', False, eta, media['info']['year'], single = True):
                    coming_soon = True

                if coming_soon:

                    # Don't list older movies
                    if ((not late and (media['info']['year'] >= now_year - 1) and (not eta.get('dvd') and not eta.get('theater') or eta.get('dvd') and eta.get('dvd') > (now - 2419200))) or
                            (late and (media['info']['year'] < now_year - 1 or (eta.get('dvd', 0) > 0 or eta.get('theater')) and eta.get('dvd') < (now - 2419200)))):

                        add = True

                        # Check if it doesn't have any releases
                        if late:
                            media['releases'] = fireEvent('release.for_media', media['_id'], single = True)
                            
                            for release in media.get('releases'):
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

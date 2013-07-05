from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Movie
from sqlalchemy.orm import joinedload_all
import random as rndm
import time

log = CPLog(__name__)


class Dashboard(Plugin):

    def __init__(self):
        addApiView('dashboard.soon', self.getSoonView)

    def getSoonView(self, limit_offset = None, random = False, late = False, **kwargs):

        db = get_session()
        now = time.time()

        # Get profiles first, determine pre or post theater
        profiles = fireEvent('profile.all', single = True)
        qualities = fireEvent('quality.all', single = True)
        pre_releases = fireEvent('quality.pre_releases', single = True)

        id_pre = {}
        for quality in qualities:
            id_pre[quality.get('id')] = quality.get('identifier') in pre_releases

        # See what the profile contain and cache it
        profile_pre = {}
        for profile in profiles:
            contains = {}
            for profile_type in profile.get('types', []):
                contains['theater' if id_pre.get(profile_type.get('quality_id')) else 'dvd'] = True

            profile_pre[profile.get('id')] = contains

        # Get all active movies
        active_status, snatched_status, downloaded_status, available_status = fireEvent('status.get', ['active', 'snatched', 'downloaded', 'available'], single = True)
        subq = db.query(Movie).filter(Movie.status_id == active_status.get('id')).subquery()

        q = db.query(Movie).join((subq, subq.c.id == Movie.id)) \
            .options(joinedload_all('releases')) \
            .options(joinedload_all('profile.types')) \
            .options(joinedload_all('library.titles')) \
            .options(joinedload_all('library.files')) \
            .options(joinedload_all('status')) \
            .options(joinedload_all('files'))

        # Add limit
        limit = 12
        if limit_offset:
            splt = splitString(limit_offset) if isinstance(limit_offset, (str, unicode)) else limit_offset
            limit = tryInt(splt[0])

        all_movies = q.all()

        if random:
            rndm.shuffle(all_movies)

        movies = []
        for movie in all_movies:
            pp = profile_pre.get(movie.profile.id)
            eta = movie.library.info.get('release_date', {}) or {}
            coming_soon = False

            # Theater quality
            if pp.get('theater') and fireEvent('searcher.could_be_released', True, eta, movie.library.year, single = True):
                coming_soon = True
            if pp.get('dvd') and fireEvent('searcher.could_be_released', False, eta, movie.library.year, single = True):
                coming_soon = True

            # Skip if movie is snatched/downloaded/available
            skip = False
            for release in movie.releases:
                if release.status_id in [snatched_status.get('id'), downloaded_status.get('id'), available_status.get('id')]:
                    skip = True
                    break
            if skip:
                continue

            if coming_soon:
                temp = movie.to_dict({
                    'profile': {'types': {}},
                    'releases': {'files':{}, 'info': {}},
                    'library': {'titles': {}, 'files':{}},
                    'files': {},
                })

                # Don't list older movies
                if ((not late and ((not eta.get('dvd') and not eta.get('theater')) or (eta.get('dvd') and eta.get('dvd') > (now - 2419200)))) or \
                        (late and (eta.get('dvd', 0) > 0 or eta.get('theater')) and eta.get('dvd') < (now - 2419200))):
                    movies.append(temp)

                if len(movies) >= limit:
                    break

        db.expire_all()
        return {
            'success': True,
            'empty': len(movies) == 0,
            'movies': movies,
        }

    getLateView = getSoonView

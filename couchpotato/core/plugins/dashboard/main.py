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

        # Add limit
        limit = 12
        if limit_offset:
            splt = splitString(limit_offset) if isinstance(limit_offset, (str, unicode)) else limit_offset
            limit = tryInt(splt[0])

        # Get all active movies
        active_status = fireEvent('status.get', ['active'], single = True)
        active = db.query(Movie) \
            .filter(Movie.status_id == active_status.get('id')) \
            .all()
        all_movie_ids = [r.id for r in active]

        # Do the shuffle
        if random:
            rndm.shuffle(all_movie_ids)

        group_limit = limit * 5
        group_offset = 0
        movies = []

        while group_offset < len(all_movie_ids) and len(movies) < limit:

            movie_ids = all_movie_ids[group_offset:group_offset + group_limit]
            group_offset += group_limit

            # Only joined needed
            q = db.query(Movie) \
                .options(joinedload_all('library')) \
                .filter(Movie.id.in_(movie_ids))
            all_movies = q.all()

            for movie in all_movies:
                pp = profile_pre.get(movie.profile_id)
                if not pp: continue

                eta = movie.library.info.get('release_date', {}) or {}
                coming_soon = False

                # Theater quality
                if pp.get('theater') and fireEvent('movie.searcher.could_be_released', True, eta, movie.library.year, single = True):
                    coming_soon = True
                elif pp.get('dvd') and fireEvent('movie.searcher.could_be_released', False, eta, movie.library.year, single = True):
                    coming_soon = True

                if coming_soon:

                    # Don't list older movies
                    if ((not late and (not eta.get('dvd') and not eta.get('theater') or eta.get('dvd') and eta.get('dvd') > (now - 2419200))) or
                            (late and (eta.get('dvd', 0) > 0 or eta.get('theater')) and eta.get('dvd') < (now - 2419200))):
                        movies.append(movie.id)

                        if len(movies) >= limit:
                            break

        # Get all movie information
        movies_raw = db.query(Movie) \
            .options(joinedload_all('library.titles')) \
            .options(joinedload_all('library.files')) \
            .options(joinedload_all('files')) \
            .filter(Movie.id.in_(movies)) \
            .all()

        movies = []
        for r in movies_raw:
            movies.append(r.to_dict({
                'library': {'titles': {}, 'files':{}},
                'files': {},
            }))

        return {
            'success': True,
            'empty': len(movies) == 0,
            'movies': movies,
        }

    getLateView = getSoonView

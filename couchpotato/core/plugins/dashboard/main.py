from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Media, Library, LibraryTitle, \
    Release
from sqlalchemy.orm import joinedload_all
from sqlalchemy.sql.expression import asc, or_
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
        active_status, ignored_status = fireEvent('status.get', ['active', 'ignored'], single = True)
        q = db.query(Media) \
            .join(Library) \
            .outerjoin(Media.releases) \
            .filter(Media.status_id == active_status.get('id')) \
            .with_entities(Media.id, Media.profile_id, Library.info, Library.year) \
            .group_by(Media.id) \
            .filter(or_(Release.id == None, Release.status_id == ignored_status.get('id')))

        if not random:
            q = q.join(LibraryTitle) \
                .filter(LibraryTitle.default == True) \
                .order_by(asc(LibraryTitle.simple_title))

        active = q.all()
        movies = []

        if len(active) > 0:

            # Do the shuffle
            if random:
                rndm.shuffle(active)

            movie_ids = []
            for movie in active:
                movie_id, profile_id, info, year = movie

                pp = profile_pre.get(profile_id)
                if not pp: continue

                eta = info.get('release_date', {}) or {}
                coming_soon = False

                # Theater quality
                if pp.get('theater') and fireEvent('movie.searcher.could_be_released', True, eta, year, single = True):
                    coming_soon = True
                elif pp.get('dvd') and fireEvent('movie.searcher.could_be_released', False, eta, year, single = True):
                    coming_soon = True

                if coming_soon:

                    # Don't list older movies
                    if ((not late and (not eta.get('dvd') and not eta.get('theater') or eta.get('dvd') and eta.get('dvd') > (now - 2419200))) or
                            (late and (eta.get('dvd', 0) > 0 or eta.get('theater')) and eta.get('dvd') < (now - 2419200))):
                        movie_ids.append(movie_id)

                        if len(movie_ids) >= limit:
                            break

            if len(movie_ids) > 0:

                # Get all movie information
                movies_raw = db.query(Media) \
                    .options(joinedload_all('library.titles')) \
                    .options(joinedload_all('library.files')) \
                    .options(joinedload_all('files')) \
                    .filter(Media.id.in_(movie_ids)) \
                    .all()

                # Create dict by movie id
                movie_dict = {}
                for movie in movies_raw:
                    movie_dict[movie.id] = movie

                for movie_id in movie_ids:
                    movies.append(movie_dict[movie_id].to_dict({
                        'library': {'titles': {}, 'files': {}},
                        'files': {},
                    }))

        return {
            'success': True,
            'empty': len(movies) == 0,
            'movies': movies,
        }

    getLateView = getSoonView

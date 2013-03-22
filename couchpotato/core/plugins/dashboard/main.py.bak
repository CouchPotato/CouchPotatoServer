from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.request import jsonified, getParams
from couchpotato.core.helpers.variable import splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Movie
from sqlalchemy.sql.expression import or_
import random

log = CPLog(__name__)


class Dashboard(Plugin):

    def __init__(self):

        addApiView('dashboard.suggestions', self.suggestView)
        addApiView('dashboard.soon', self.getSoonView)

    def newSuggestions(self):

        movies = fireEvent('movie.list', status = ['active', 'done'], limit_offset = (20, 0), single = True)
        movie_identifiers = [m['library']['identifier'] for m in movies[1]]

        ignored_movies = fireEvent('movie.list', status = ['ignored', 'deleted'], limit_offset = (100, 0), single = True)
        ignored_identifiers = [m['library']['identifier'] for m in ignored_movies[1]]

        suggestions = fireEvent('movie.suggest', movies = movie_identifiers, ignore = ignored_identifiers, single = True)
        suggest_status = fireEvent('status.get', 'suggest', single = True)

        for suggestion in suggestions:
            fireEvent('movie.add', params = {'identifier': suggestion}, force_readd = False, search_after = False, status_id = suggest_status.get('id'))

    def suggestView(self):

        db = get_session()

        movies = db.query(Movie).limit(20).all()
        identifiers = [m.library.identifier for m in movies]

        suggestions = fireEvent('movie.suggest', movies = identifiers, single = True)
        print suggestions

        return jsonified({
            'result': True,
            'suggestions': suggestions
        })

    def getSoonView(self):

        params = getParams()
        db = get_session()

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
        q = db.query(Movie) \
            .join(Movie.profile, Movie.library) \
            .filter(or_(*[Movie.status.has(identifier = s) for s in ['active']])) \
            .group_by(Movie.id)

        # Add limit
        limit_offset = params.get('limit_offset')
        limit = 12
        if limit_offset:
            splt = splitString(limit_offset) if isinstance(limit_offset, (str, unicode)) else limit_offset
            limit = tryInt(splt[0])

        all_movies = q.all()

        if params.get('random', False):
            random.shuffle(all_movies)

        movies = []
        for movie in all_movies:
            pp = profile_pre.get(movie.profile.id)
            eta = movie.library.info.get('release_date', {})
            coming_soon = False

            # Theater quality
            if pp.get('theater') and fireEvent('searcher.could_be_released', True, eta, single = True):
                coming_soon = True
            if pp.get('dvd') and fireEvent('searcher.could_be_released', False, eta, single = True):
                coming_soon = True

            if coming_soon:
                temp = movie.to_dict({
                    'profile': {'types': {}},
                    'releases': {'files':{}, 'info': {}},
                    'library': {'titles': {}, 'files':{}},
                    'files': {},
                })
                movies.append(temp)

                if len(movies) >= limit:
                    break

        return jsonified({
            'success': True,
            'empty': len(movies) == 0,
            'movies': movies,
        })

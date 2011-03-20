from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.request import getParams, jsonified
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Movie, Release, Profile
from couchpotato.environment import Env
from urllib import urlencode


class MoviePlugin(Plugin):

    def __init__(self):
        addApiView('movie.search', self.search)
        addApiView('movie.list', self.list)
        addApiView('movie.add', self.add)

    def list(self):

        a = getParams()

        results = get_session().query(Movie).filter(
                Movie.releases.any(
                    Release.status.has(identifier = 'wanted')
                )
            ).all()

        movies = []
        for movie in results:
            temp = {
                'id': movie.id,
                'name': movie.id,
                'releases': [],
            }
            for release in movie.releases:
                temp['releases'].append({
                    'status': release.status.label,
                    'quality': release.quality.label
                })

            movies.append(temp)

        return jsonified({
            'success': True,
            'empty': len(movies) == 0,
            'movies': movies,
        })

    def search(self):

        a = getParams()
        cache_key = '%s/%s' % (__name__, urlencode(a))
        movies = Env.get('cache').get(cache_key)

        if not movies:
            results = fireEvent('provider.movie.search', q = a.get('q'))

            # Combine movie results
            movies = []
            for r in results:
                movies += r

            Env.get('cache').set(cache_key, movies, timeout = 10)


        return jsonified({
            'success': True,
            'empty': len(movies) == 0,
            'movies': movies,
        })

    def add(self):

        a = getParams()
        db = get_session();

        library = fireEvent('library.add', attrs = a)
        profile = db.query(Profile).filter_by(identifier = a.get('profile_identifier'))

        m = db.query(Movie).filter_by(library = library).first()

        if not m:
            m = Movie(
                library = library,
                profile = profile,
            )
            db.add(m)
            db.commit()

        return jsonified({
            'success': True,
            'added': True,
            'params': a,
        })

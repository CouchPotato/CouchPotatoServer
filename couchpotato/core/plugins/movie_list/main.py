from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.helpers.request import getParams, jsonified
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Movie, Release

class MovieList(Plugin):

    def __init__(self):
        addApiView('movie.list', self.list)

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

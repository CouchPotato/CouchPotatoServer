from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.request import getParams, jsonified
from couchpotato.core.plugins.base import Plugin

class MovieAdd(Plugin):

    def __init__(self):
        addApiView('movie.add.search', self.search)
        addApiView('movie.add.select', self.select)

    def search(self):

        a = getParams()

        results = fireEvent('provider.movie.search', q = a.get('q'))

        # Combine movie results
        movies = []
        for r in results:
            movies += r

        return jsonified({
            'success': True,
            'empty': len(movies) == 0,
            'movies': movies,
        })

    def select(self):

        a = getParams()

        return jsonified({
            'success': True,
            'added': True,
        })

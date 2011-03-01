from couchpotato.api import addApiView
from couchpotato.core.event import getEvent, fireEvent
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from flask.helpers import jsonify

class MovieAdd(Plugin):

    def __init__(self):
        addApiView('movie.add.search', self.search)

    def search(self):

        a = Env.getParams()

        print fireEvent('provider.movie.search', q = a.get('q'))

        movies = [
            {'id': 1, 'name': 'test'}
        ]

        return jsonify({
            'success': True,
            'empty': len(movies) == 0,
            'movies': movies,
        })


    def select(self):
        pass

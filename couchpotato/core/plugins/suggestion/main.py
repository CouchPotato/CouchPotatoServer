from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.plugins.base import Plugin

class Suggestion(Plugin):

    def __init__(self):

        addApiView('suggestion.view', self.getView)

    def getView(self, limit_offset = None, **kwargs):

        total_movies, movies = fireEvent('movie.list', status = 'suggest', limit_offset = limit_offset, single = True)

        return {
            'success': True,
            'empty': len(movies) == 0,
            'total': total_movies,
            'movies': movies,
        }

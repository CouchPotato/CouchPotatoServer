from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.request import jsonified, getParam
from couchpotato.core.plugins.base import Plugin

class Suggestion(Plugin):

    def __init__(self):

        addApiView('suggestion.view', self.getView)

    def getView(self):

        limit_offset = getParam('limit_offset', None)
        total_movies, movies = fireEvent('movie.list', status = 'suggest', limit_offset = limit_offset, single = True)

        return jsonified({
            'success': True,
            'empty': len(movies) == 0,
            'total': total_movies,
            'movies': movies,
        })

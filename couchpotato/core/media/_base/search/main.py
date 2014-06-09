from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.variable import mergeDicts, getImdb
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class Search(Plugin):

    def __init__(self):

        addApiView('search', self.search, docs = {
            'desc': 'Search the info in providers for a movie',
            'params': {
                'q': {'desc': 'The (partial) movie name you want to search for'},
                'type': {'desc': 'Search for a specific media type. Leave empty to search all.'},
            },
            'return': {'type': 'object', 'example': """{
    'success': True,
    'movies': array,
    'show': array,
    etc
}"""}
        })

        addEvent('app.load', self.addSingleSearches)

    def search(self, q = '', types = None, **kwargs):

        # Make sure types is the correct instance
        if isinstance(types, (str, unicode)):
            types = [types]
        elif isinstance(types, (list, tuple, set)):
            types = list(types)

        imdb_identifier = getImdb(q)

        if not types:
            if imdb_identifier:
                result = fireEvent('movie.info', identifier = imdb_identifier, merge = True)
                result = {result['type']: [result]}
            else:
                result = fireEvent('info.search', q = q, merge = True)
        else:
            result = {}
            for media_type in types:
                if imdb_identifier:
                    result[media_type] = fireEvent('%s.info' % media_type, identifier = imdb_identifier)
                else:
                    result[media_type] = fireEvent('%s.search' % media_type, q = q)

        return mergeDicts({
            'success': True,
        }, result)

    def createSingleSearch(self, media_type):

        def singleSearch(q, **kwargs):
            return self.search(q, type = media_type, **kwargs)

        return singleSearch

    def addSingleSearches(self):

        for media_type in fireEvent('media.types', merge = True):
            addApiView('%s.search' % media_type, self.createSingleSearch(media_type))

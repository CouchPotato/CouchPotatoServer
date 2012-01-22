from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.request import jsonified, getParams
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.movie.base import MovieProvider
from couchpotato.core.settings.model import Movie
from flask.helpers import json

log = CPLog(__name__)


class CouchPotatoApi(MovieProvider):

    apiUrl = 'http://couchpota.to/api/%s/'

    def __init__(self):
        addEvent('movie.release_date', self.releaseDate)
        addApiView('movie.suggest', self.suggestView)

    def releaseDate(self, imdb_id):

        try:
            data = self.urlopen((self.apiUrl % ('eta')) + (id + '/'))
            dates = json.loads(data)
            log.info('Found ETA for %s: %s' % (imdb_id, dates))
        except Exception, e:
            log.error('Error getting ETA for %s: %s' % (imdb_id, e))

        return dates

    def suggest(self, movies = [], ignore = []):
        try:
            data = self.urlopen((self.apiUrl % ('suggest')) + ','.join(movies) + '/' + ','.join(ignore) + '/')
            suggestions = json.loads(data)
            log.info('Found Suggestions for %s' % (suggestions))
        except Exception, e:
            log.error('Error getting suggestions for %s: %s' % (movies, e))

        return suggestions

    def suggestView(self):

        params = getParams()
        movies = params.get('movies')
        ignore = params.get('ignore', [])

        if not movies:
            db = get_session()
            active_movies = db.query(Movie).filter(Movie.status.has(identifier = 'active')).all()
            movies = [x.library.identifier for x in active_movies]

        suggestions = self.suggest(movies, ignore)

        return jsonified({
            'success': True,
            'count': len(suggestions),
            'suggestions': suggestions
        })

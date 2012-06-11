from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.request import jsonified, getParams
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.movie.base import MovieProvider
from couchpotato.core.settings.model import Movie
from flask.helpers import json

log = CPLog(__name__)


class CouchPotatoApi(MovieProvider):

    api_url = 'http://couchpota.to/api/%s/'
    http_time_between_calls = 0

    def __init__(self):
        #addApiView('movie.suggest', self.suggestView)

        addEvent('movie.info', self.getInfo)
        addEvent('movie.release_date', self.getReleaseDate)

    def getInfo(self, identifier = None):
        return {
            'release_date': self.getReleaseDate(identifier)
        }

    def getReleaseDate(self, identifier = None):

        if identifier is None: return {}
        try:
            headers = {'X-CP-Version': fireEvent('app.version', single = True)}
            data = self.urlopen((self.api_url % ('eta')) + (identifier + '/'), headers = headers)
            dates = json.loads(data)
            log.debug('Found ETA for %s: %s', (identifier, dates))
            return dates
        except Exception, e:
            log.error('Error getting ETA for %s: %s', (identifier, e))

        return {}

    def suggest(self, movies = [], ignore = []):
        try:
            data = self.urlopen((self.api_url % ('suggest')) + ','.join(movies) + '/' + ','.join(ignore) + '/')
            suggestions = json.loads(data)
            log.info('Found Suggestions for %s', (suggestions))
        except Exception, e:
            log.error('Error getting suggestions for %s: %s', (movies, e))

        return suggestions

    def suggestView(self):

        params = getParams()
        movies = params.get('movies')
        ignore = params.get('ignore', [])

        if not movies:
            db = get_session()
            active_movies = db.query(Movie).filter(Movie.status.has(identifier = 'active')).all()
            movies = [x.library.identifier for x in active_movies]
            #db.close()

        suggestions = self.suggest(movies, ignore)

        return jsonified({
            'success': True,
            'count': len(suggestions),
            'suggestions': suggestions
        })

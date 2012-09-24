from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.request import jsonified, getParams
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.movie.base import MovieProvider
from couchpotato.core.settings.model import Movie
from flask.helpers import json
import time
import traceback

log = CPLog(__name__)


class CouchPotatoApi(MovieProvider):

    urls = {
        'search': 'https://couchpota.to/api/search/%s/',
        'info': 'https://couchpota.to/api/info/%s/',
        'eta': 'https://couchpota.to/api/eta/%s/',
        'suggest': 'https://couchpota.to/api/suggest/%s/%s/',
    }
    http_time_between_calls = 0
    api_version = 1

    def __init__(self):
        #addApiView('movie.suggest', self.suggestView)

        addEvent('movie.info', self.getInfo, priority = 1)
        addEvent('movie.search', self.search, priority = 1)
        addEvent('movie.release_date', self.getReleaseDate)

    def search(self, q, limit = 12):

        cache_key = 'cpapi.cache.%s' % q
        cached = self.getCache(cache_key, self.urls['search'] % tryUrlencode(q), timeout = 3, headers = self.getRequestHeaders())

        if cached:
            try:
                movies = json.loads(cached)
                return movies
            except:
                log.error('Failed parsing search results: %s', traceback.format_exc())

        return []

    def getInfo(self, identifier = None):

        if not identifier:
            return

        cache_key = 'cpapi.cache.info.%s' % identifier
        cached = self.getCache(cache_key, self.urls['info'] % identifier, timeout = 3, headers = self.getRequestHeaders())

        if cached:
            try:
                movie = json.loads(cached)
                return movie
            except:
                log.error('Failed parsing info results: %s', traceback.format_exc())

        return {}

    def getReleaseDate(self, identifier = None):

        if identifier is None: return {}
        try:
            data = self.urlopen(self.urls['eta'] % identifier, headers = self.getRequestHeaders())
            dates = json.loads(data)
            log.debug('Found ETA for %s: %s', (identifier, dates))
            return dates
        except Exception, e:
            log.error('Error getting ETA for %s: %s', (identifier, e))

        return {}

    def suggest(self, movies = [], ignore = []):
        try:
            data = self.urlopen(self.urls['suggest'] % (','.join(movies), ','.join(ignore)))
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

    def getRequestHeaders(self):
        return {
            'X-CP-Version': fireEvent('app.version', single = True),
            'X-CP-API': self.api_version,
            'X-CP-Time': time.time(),
        }

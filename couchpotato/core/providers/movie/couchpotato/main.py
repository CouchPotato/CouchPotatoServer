from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import MovieProvider
from flask.helpers import json

log = CPLog(__name__)


class CouchPotatoApi(MovieProvider):

    apiUrl = 'http://couchpotatoapp.com/api/%s/%s/'

    def __init__(self):

        addEvent('provider.movie.release_date', self.releaseDate)

    def releaseDate(self, imdb_id):

        data = self.urlopen(self.apiUrl % ('eta', id))

        try:
            dates = json.loads(data)
            log.info('Found ETA for %s: %s' % (imdb_id, dates))
        except Exception, e:
            log.error('Error getting ETA for %s: %s' % (imdb_id, e))

        return dates
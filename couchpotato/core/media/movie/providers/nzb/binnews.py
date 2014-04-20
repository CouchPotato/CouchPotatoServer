from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.nzb.binnewz.main import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'BinNewz'


class BinNewz(MovieProvider, Base):

    def buildUrl(self, media, api_key):
        query = tryUrlencode({
            't': 'movie',
            'imdbid': getIdentifier(media).replace('tt', ''),
            'apikey': api_key,
            'extended': 1
        })
        return query

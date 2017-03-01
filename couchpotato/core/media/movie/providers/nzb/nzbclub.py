from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.nzb.nzbclub import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'NZBClub'


class NZBClub(MovieProvider, Base):

    def buildUrl(self, media):

        q = tryUrlencode({
            'q': '%s' % fireEvent('library.query', media, single = True),
        })

        query = tryUrlencode({
            'ig': 1,
            'rpp': 200,
            'st': 5,
            'sp': 1,
            'ns': 1,
        })
        return '%s&%s' % (q, query)

from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.och.hdarea import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'hdarea'


class hdarea(MovieProvider, Base):
    def buildUrl(self, media, quality):
        title = fireEvent('library.query', media, include_year=False, single=True)

        query = '"%s"' % (tryUrlencode(title)),

        return query

from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.torrent.torrentz import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'Torrentz'


class Torrentz(MovieProvider, Base):

    def buildUrl(self, media):
        return tryUrlencode('"%s"' % fireEvent('library.query', media, single = True))

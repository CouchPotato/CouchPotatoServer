from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.magnetdl import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'MagnetDL'


class MagnetDL(MovieProvider, Base):
    pass

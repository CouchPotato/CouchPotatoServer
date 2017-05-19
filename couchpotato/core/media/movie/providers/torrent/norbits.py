from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.norbits import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'Norbits'


class Norbits(MovieProvider, Base):
   pass

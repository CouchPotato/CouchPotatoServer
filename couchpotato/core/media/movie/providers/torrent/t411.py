from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.t411 import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'T411'


class T411(MovieProvider, Base):
    pass

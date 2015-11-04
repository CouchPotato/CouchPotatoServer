from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.cpasbien import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'cpasbien'


class cpasbien(MovieProvider, Base):
    pass

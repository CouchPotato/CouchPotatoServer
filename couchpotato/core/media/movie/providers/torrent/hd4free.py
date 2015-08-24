from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.hd4free import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'HD4Free'


class HD4Free(MovieProvider, Base):
    pass

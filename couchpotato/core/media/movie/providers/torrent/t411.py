from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.t411 import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 't411'


class t411(MovieProvider, Base):
    pass

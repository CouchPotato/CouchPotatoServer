from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.hdbits.main import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)


class HDBits(MovieProvider, Base):
    pass

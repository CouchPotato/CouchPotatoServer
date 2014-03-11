from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.yify.main import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)


class Yify(MovieProvider, Base):
    pass

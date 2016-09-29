from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.gimmepeers import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'GimmePeers'


class GimmePeers(MovieProvider, Base):
    pass

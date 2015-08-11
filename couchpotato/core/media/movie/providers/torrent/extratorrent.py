from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.extratorrent import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'ExtraTorrent'


class ExtraTorrent(MovieProvider, Base):

    category = 4

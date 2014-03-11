from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.awesomehd.main import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'AwesomeHD'


class AwesomeHD(MovieProvider, Base):
    pass

from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.kickasstorrents import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'KickAssTorrents'


class KickAssTorrents(MovieProvider, Base):
    pass

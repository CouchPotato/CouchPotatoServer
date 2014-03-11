from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.torrent.publichd.main import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)


class PublicHD(MovieProvider, Base):

    def buildUrl(self, media):
        return fireEvent('library.query', media, single = True)

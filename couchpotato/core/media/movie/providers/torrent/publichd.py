from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.torrent.publichd import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'PublicHD'


class PublicHD(MovieProvider, Base):

    def buildUrl(self, media):
        return fireEvent('library.query', media, single = True).replace(':', '')

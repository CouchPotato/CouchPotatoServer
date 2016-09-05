from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.torrentz2 import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'Torrentz2'


class Torrentz2(MovieProvider, Base):

    def buildUrl(self, title, media, quality):
        return tryUrlencode('"%s %s"' % (title, media['info']['year']))

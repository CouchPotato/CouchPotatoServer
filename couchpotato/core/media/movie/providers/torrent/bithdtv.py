from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.torrent.bithdtv import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'BiTHDTV'


class BiTHDTV(MovieProvider, Base):

    def buildUrl(self, media):
        query = tryUrlencode({
            'search': fireEvent('library.query', media, single = True),
            'cat': 7  # Movie cat
        })
        return query

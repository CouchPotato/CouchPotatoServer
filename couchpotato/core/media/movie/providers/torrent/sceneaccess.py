from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.sceneaccess import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'SceneAccess'


class SceneAccess(MovieProvider, Base):

    cat_ids = [
        ([22], ['720p', '1080p']),
        ([7], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
        ([8], ['dvdr']),
    ]

    def buildUrl(self, media, quality):
        url = self.urls['search'] % (
            self.getCatId(quality['identifier'])[0],
            self.getCatId(quality['identifier'])[0]
        )

        arguments = tryUrlencode({
            'search': fireEvent('library.query', media, single = True),
            'method': 3,
        })
        query = "%s&%s" % (url, arguments)

        return query

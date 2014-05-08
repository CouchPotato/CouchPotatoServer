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

    def buildUrl(self, title, media, quality):
        cat_id = self.getCatId(quality)[0]
        url = self.urls['search'] % (cat_id, cat_id)

        arguments = tryUrlencode({
            'search': '"%s" %s' % (title, media['info']['year']),
            'method': 2,
        })
        query = "%s&%s" % (url, arguments)

        return query

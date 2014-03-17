from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.torrent.sceneaccess import Base


log = CPLog(__name__)

autoload = 'SceneAccess'


class SceneAccess(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):

    cat_ids = [
        ([26], ['hdtv_sd', 'hdtv_720p', 'webdl_720p', 'webdl_1080p']),
    ]

    def buildUrl(self, media, quality):
        url = self.urls['archive'] % (
            self.getCatId(quality['identifier'])[0],
            self.getCatId(quality['identifier'])[0]
        )

        arguments = tryUrlencode({
            'search': fireEvent('media.search_query', media, single = True),
            'method': 3,
        })
        query = "%s&%s" % (url, arguments)

        return query


class Episode(EpisodeProvider, Base):

    cat_ids = [
        ([27], ['hdtv_720p', 'webdl_720p', 'webdl_1080p']),
        ([17, 11], ['hdtv_sd'])
    ]

    def buildUrl(self, media, quality):
        url = self.urls['search'] % (
            self.getCatId(quality['identifier'])[0],
            self.getCatId(quality['identifier'])[0]
        )

        arguments = tryUrlencode({
            'search': fireEvent('media.search_query', media, single = True),
            'method': 3,
        })
        query = "%s&%s" % (url, arguments)

        return query

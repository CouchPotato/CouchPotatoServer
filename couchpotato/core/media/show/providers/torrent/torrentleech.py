from couchpotato import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.torrent.torrentleech import Base

log = CPLog(__name__)

autoload = 'TorrentLeech'


class TorrentLeech(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):

    cat_ids = [
        ([27], ['hdtv_sd', 'hdtv_720p', 'webdl_720p', 'webdl_1080p']),
    ]

    def buildUrl(self, media, quality):
        return (
            tryUrlencode(fireEvent('media.search_query', media, single = True)),
            self.getCatId(quality['identifier'])[0]
        )

class Episode(EpisodeProvider, Base):

    cat_ids = [
        ([32], ['hdtv_720p', 'webdl_720p', 'webdl_1080p']),
        ([26], ['hdtv_sd'])
    ]

    def buildUrl(self, media, quality):
        return (
            tryUrlencode(fireEvent('media.search_query', media, single = True)),
            self.getCatId(quality['identifier'])[0]
        )

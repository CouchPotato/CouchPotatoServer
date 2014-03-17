from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.torrent.torrentday import Base

log = CPLog(__name__)

autoload = 'TorrentDay'


class TorrentDay(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):

    cat_ids = [
        ([14], ['hdtv_sd', 'hdtv_720p', 'webdl_720p', 'webdl_1080p']),
    ]
    def buildUrl(self, media):
        return fireEvent('media.search_query', media, single = True)


class Episode(EpisodeProvider, Base):
    cat_ids = [
        ([7], ['hdtv_720p', 'webdl_720p', 'webdl_1080p']),
        ([2], [24], [26], ['hdtv_sd'])
    ]
    def buildUrl(self, media):
        return fireEvent('media.search_query', media, single = True)


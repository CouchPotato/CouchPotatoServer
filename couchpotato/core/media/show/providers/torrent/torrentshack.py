from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.torrent.torrentshack import Base

log = CPLog(__name__)

autoload = 'TorrentShack'


class TorrentShack(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):
    # TorrentShack tv season search categories
    #   TV-SD Pack - 980
    #   TV-HD Pack - 981
    #   Full Blu-ray - 970
    cat_ids = [
        ([980], ['hdtv_sd']),
        ([981], ['hdtv_720p', 'webdl_720p', 'webdl_1080p', 'bdrip_1080p', 'bdrip_720p', 'brrip_1080p', 'brrip_720p']),
        ([970], ['bluray_1080p', 'bluray_720p']),
    ]
    cat_backup_id = 980

    def buildUrl(self, media, quality):
        query = (tryUrlencode(fireEvent('media.search_query', media, single = True)),
                 self.getCatId(quality['identifier'])[0],
                 self.getSceneOnly())
        return query

class Episode(EpisodeProvider, Base):
    # TorrentShack tv episode search categories
    #   TV/x264-HD - 600
    #   TV/x264-SD - 620
    #   TV/DVDrip - 700
    cat_ids = [
        ([600], ['hdtv_720p', 'webdl_720p', 'webdl_1080p', 'bdrip_1080p', 'bdrip_720p', 'brrip_1080p', 'brrip_720p']),
        ([620], ['hdtv_sd'])
    ]
    cat_backup_id = 620

    def buildUrl(self, media, quality):
        query = (tryUrlencode(fireEvent('media.search_query', media, single = True)),
                 self.getCatId(quality['identifier'])[0],
                 self.getSceneOnly())
        return query

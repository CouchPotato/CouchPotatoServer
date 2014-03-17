from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.torrent.bitsoup import Base

log = CPLog(__name__)

autoload = 'Bitsoup'


class Bitsoup(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):
    # For season bundles, bitsoup currently only has one category
    def buildUrl(self, media, quality):
        query = tryUrlencode({
            'search': fireEvent('media.search_query', media, single = True),
            'cat': 45 # TV-Packs Category
        })
        return query


class Episode(EpisodeProvider, Base):
    cat_ids = [
        ([42], ['hdtv_720p', 'webdl_720p', 'webdl_1080p', 'bdrip_1080p', 'bdrip_720p', 'brrip_1080p', 'brrip_720p']),
        ([49], ['hdtv_sd', 'webdl_480p'])
    ]
    cat_backup_id = 0

    def buildUrl(self, media, quality):
        query = tryUrlencode({
            'search': fireEvent('media.search_query', media, single = True),
            'cat': self.getCatId(quality['identifier'])[0],
        })
        return query

from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.torrent.iptorrents import Base

log = CPLog(__name__)

autoload = 'IPTorrents'


class IPTorrents(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):

    # TODO come back to this later, a better quality system needs to be created
    cat_ids = [
        ([65], [
            'bluray_1080p', 'bluray_720p',
            'bdrip_1080p', 'bdrip_720p',
            'brrip_1080p', 'brrip_720p',
            'webdl_1080p', 'webdl_720p', 'webdl_480p',
            'hdtv_720p', 'hdtv_sd'
        ]),
    ]


class Episode(EpisodeProvider, Base):

    # TODO come back to this later, a better quality system needs to be created
    cat_ids = [
        ([5], ['hdtv_720p', 'webdl_720p', 'webdl_1080p']),
        ([4, 78, 79], ['hdtv_sd'])
    ]

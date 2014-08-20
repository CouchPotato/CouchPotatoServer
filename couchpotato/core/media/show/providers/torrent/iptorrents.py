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
    cat_ids = [
        ([65], {}),
    ]


class Episode(EpisodeProvider, Base):
    cat_ids = [
        ([4],  {'codec': ['mp4-asp'], 'resolution': ['sd'],            'source': ['hdtv', 'web']}),
        ([5],  {'codec': ['mp4-avc'], 'resolution': ['720p', '1080p'], 'source': ['hdtv', 'web']}),
        ([78], {'codec': ['mp4-avc'], 'resolution': ['480p'],          'source': ['hdtv', 'web']}),
        ([79], {'codec': ['mp4-avc'], 'resolution': ['sd'],            'source': ['hdtv', 'web']})
    ]

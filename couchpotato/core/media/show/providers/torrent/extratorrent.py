from couchpotato.core.logger import CPLog

from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.torrent.extratorrent import Base

log = CPLog(__name__)

autoload = 'ExtraTorrent'


class ExtraTorrent(MultiProvider):

    def getTypes(self):
        return [Season, Episode]

class Season(SeasonProvider, Base):

    category = 8


class Episode(EpisodeProvider, Base):

    category = 8

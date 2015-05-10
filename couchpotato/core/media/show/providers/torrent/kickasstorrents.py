from couchpotato.core.logger import CPLog

from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.torrent.kickasstorrents import Base

log = CPLog(__name__)

autoload = 'KickAssTorrents'


class KickAssTorrents(MultiProvider):

    def getTypes(self):
        return [Season, Episode]

class Season(SeasonProvider, Base):

    urls = {
        'detail': '%s/%%s',
        'search': '%s/usearch/%s category:tv/%d/',
    }

    # buildUrl does not need an override


class Episode(EpisodeProvider, Base):

    urls = {
        'detail': '%s/%%s',
        'search': '%s/usearch/%s category:tv/%d/',
    }

    # buildUrl does not need an override

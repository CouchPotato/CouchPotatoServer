from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.torrent.publichd import Base

log = CPLog(__name__)

autoload = 'PublicHD'


class PublicHD(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):

    def buildUrl(self, media):
        return fireEvent('media.search_query', media, single = True)


class Episode(EpisodeProvider, Base):

    def buildUrl(self, media):
        return fireEvent('media.search_query', media, single = True)

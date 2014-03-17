from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.torrent.bithdtv import Base

log = CPLog(__name__)

autoload = 'BiTHDTV'


class BiTHDTV(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):

    def buildUrl(self, media):
        query = tryUrlencode({
            'search': fireEvent('media.search_query', media, single = True),
            'cat': 12 # Season cat
        })
        return query


class Episode(EpisodeProvider, Base):

    def buildUrl(self, media):
        query = tryUrlencode({
            'search': fireEvent('media.search_query', media, single = True),
            'cat': 10 # Episode cat
        })
        return query

from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.nzb.nzbclub import Base

log = CPLog(__name__)

autoload = 'NZBClub'


class NZBClub(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):

    def buildUrl(self, media):

        q = tryUrlencode({
            'q': fireEvent('media.search_query', media, single = True),
        })

        query = tryUrlencode({
            'ig': 1,
            'rpp': 200,
            'st': 5,
            'sp': 1,
            'ns': 1,
        })
        return '%s&%s' % (q, query)


class Episode(EpisodeProvider, Base):

    def buildUrl(self, media):

        q = tryUrlencode({
            'q': fireEvent('media.search_query', media, single = True),
        })

        query = tryUrlencode({
            'ig': 1,
            'rpp': 200,
            'st': 5,
            'sp': 1,
            'ns': 1,
        })
        return '%s&%s' % (q, query)

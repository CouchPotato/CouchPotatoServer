from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media._base.providers.nzb.newznab import Base
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider

log = CPLog(__name__)

autoload = 'Newznab'


class Newznab(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):

    def buildUrl(self, media, host):
        related = fireEvent('library.related', media, single = True)
        identifier = fireEvent('library.identifier', media, single = True)

        query = tryUrlencode({
            't': 'tvsearch',
            'apikey': host['api_key'],
            'q': related['show']['title'],
            'season': identifier['season'],
            'extended': 1
        })
        return query


class Episode(EpisodeProvider, Base):

    def buildUrl(self, media, host):
        related = fireEvent('library.related', media, single = True)
        identifier = fireEvent('library.identifier', media, single = True)
        query = tryUrlencode({
            't': 'tvsearch',
            'apikey': host['api_key'],
            'q': related['show']['title'],
            'season': identifier['season'],
            'ep': identifier['episode'],
            'extended': 1
        })

        return query

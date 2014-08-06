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

    def buildUrl(self, media, api_key):
        search_title = fireEvent('media.search_query', media, include_identifier = False, single = True)
        identifier = fireEvent('media.identifier', media, single = True)

        query = tryUrlencode({
            't': 'tvsearch',
            'q': search_title,
            'season': identifier['season'],
            'apikey': api_key,
            'extended': 1
        })
        return query


class Episode(EpisodeProvider, Base):

    def buildUrl(self, media, api_key):
        search_title = fireEvent('media.search_query', media['show'], include_identifier = False, single = True)
        identifier = fireEvent('media.identifier', media, single = True)

        query = tryUrlencode({
            't': 'tvsearch',
            'q': search_title,
            'season': identifier['season'],
            'ep': identifier['episode'],
            'apikey': api_key,
            'extended': 1
        })

        return query

from couchpotato import Env
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.nzb.nzbindex import Base

log = CPLog(__name__)

autoload = 'NzbIndex'


class NzbIndex(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):

    def buildUrl(self, media, quality):
        query = tryUrlencode({
            'q': fireEvent('media.search_query', media, single = True),
            'age': Env.setting('retention', 'nzb'),
            'sort': 'agedesc',
            'minsize': quality.get('size_min'),
            'maxsize': quality.get('size_max'),
            'rating': 1,
            'max': 250,
            'more': 1,
            'complete': 1,
        })
        return query


class Episode(EpisodeProvider, Base):

    def buildUrl(self, media, quality):
        query = tryUrlencode({
            'q': fireEvent('media.search_query', media, single = True),
            'age': Env.setting('retention', 'nzb'),
            'sort': 'agedesc',
            'minsize': quality.get('size_min'),
            'maxsize': quality.get('size_max'),
            'rating': 1,
            'max': 250,
            'more': 1,
            'complete': 1,
        })
        return query

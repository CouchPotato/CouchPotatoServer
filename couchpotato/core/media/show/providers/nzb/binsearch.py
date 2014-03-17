from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media._base.providers.nzb.binsearch import Base
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.environment import Env

log = CPLog(__name__)

autoload = 'BinSearch'


class BinSearch(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):

    def buildUrl(self, media, quality):
        query = tryUrlencode({
            'q': fireEvent('media.search_query', media, single = True),
            'm': 'n',
            'max': 400,
            'adv_age': Env.setting('retention', 'nzb'),
            'adv_sort': 'date',
            'adv_col': 'on',
            'adv_nfo': 'on',
            'minsize': quality.get('size_min'),
            'maxsize': quality.get('size_max'),
        })
        return query


class Episode(EpisodeProvider, Base):

    def buildUrl(self, media, quality):
        query = tryUrlencode({
            'q': fireEvent('media.search_query', media, single = True),
            'm': 'n',
            'max': 400,
            'adv_age': Env.setting('retention', 'nzb'),
            'adv_sort': 'date',
            'adv_col': 'on',
            'adv_nfo': 'on',
            'minsize': quality.get('size_min'),
            'maxsize': quality.get('size_max'),
        })
        return query

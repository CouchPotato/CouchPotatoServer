from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.nzb.nzbindex import Base
from couchpotato.core.media.movie.providers.base import MovieProvider
from couchpotato.environment import Env

log = CPLog(__name__)

autoload = 'NzbIndex'


class NzbIndex(MovieProvider, Base):

    def buildUrl(self, media, quality):
        title = fireEvent('library.query', media, include_year = False, single = True)
        year = media['info']['year']

        query = tryUrlencode({
            'q': '"%s %s" | "%s (%s)"' % (title, year, title, year),
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

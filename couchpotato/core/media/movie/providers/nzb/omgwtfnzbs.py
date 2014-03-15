from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.nzb.omgwtfnzbs import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'OMGWTFNZBs'


class OMGWTFNZBs(MovieProvider, Base):
    pass

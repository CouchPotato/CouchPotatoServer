from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.alpharatio import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'AlphaRatio'


class AlphaRatio(MovieProvider, Base):

    # AlphaRatio movie search categories
    # 7: MoviesHD
    # 9: MoviePackHD
    # 6: MoviesSD
    # 8: MovePackSD

    cat_ids = [
        ([7, 9], ['bd50']),
        ([7, 9], ['720p', '1080p']),
        ([6, 8], ['dvdr']),
        ([6, 8], ['brrip', 'dvdrip']),
    ]
    cat_backup_id = 6

    def buildUrl(self, media, quality):
        query = (tryUrlencode(fireEvent('library.query', media, single = True)),
                 self.getSceneOnly(),
                 self.getCatId(quality)[0])
        return query

from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.alpharatio import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'AlphaRatio'


class AlphaRatio(MovieProvider, Base):

    # AlphaRatio movie search categories
    # 10: MovieUHD
    # 13: MoviePackUHD
    # 9: MovieHD
    # 12: MoviePackHD
    # 8: MovieSD
    # 11: MoviePackSD

    cat_ids = [
        ([10, 13], ['2160p']),
        ([9, 12], ['bd50']),
        ([9, 12], ['720p', '1080p']),
        ([8, 11], ['dvdr']),
        ([8, 11], ['brrip', 'dvdrip']),
    ]
    cat_backup_id = 8

    def buildUrl(self, media, quality):
        query = (tryUrlencode(fireEvent('library.query', media, single = True)),
                 self.getSceneOnly(),
                 self.getCatId(quality)[0])
        return query

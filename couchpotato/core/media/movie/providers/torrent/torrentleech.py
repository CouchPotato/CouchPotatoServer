from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.torrentleech import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'TorrentLeech'


class TorrentLeech(MovieProvider, Base):

    cat_ids = [
        ([41, 47], ['2160p']),
        ([13, 14, 37, 43], ['720p', '1080p']),
        ([13], ['bd50']),
        ([8], ['cam']),
        ([9], ['ts', 'tc']),
        ([10, 11, 37], ['r5', 'scr']),
        ([11], ['dvdrip']),
        ([13, 14, 37, 43], ['brrip']),
        ([12], ['dvdr']),
    ]

    def buildUrl(self, title, media, quality):
        return (
            tryUrlencode(title.replace(':', '')),
            ','.join([str(x) for x in self.getCatId(quality)])
        )

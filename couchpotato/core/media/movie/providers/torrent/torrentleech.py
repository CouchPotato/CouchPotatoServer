from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.torrentleech import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'TorrentLeech'


class TorrentLeech(MovieProvider, Base):

    cat_ids = [
        ([13], ['720p', '1080p', 'bd50']),
        ([8], ['cam']),
        ([9], ['ts', 'tc']),
        ([10], ['r5', 'scr']),
        ([11], ['dvdrip']),
        ([13, 14], ['brrip']),
        ([12], ['dvdr']),
    ]

    def buildUrl(self, title, media, quality):
        return (
            tryUrlencode(title.replace(':', '')),
            ','.join([str(x) for x in self.getCatId(quality)])
        )

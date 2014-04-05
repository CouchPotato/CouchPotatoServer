from couchpotato import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.torrentleech import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'TorrentLeech'


class TorrentLeech(MovieProvider, Base):

    cat_ids = [
        ([13], ['720p', '1080p']),
        ([8], ['cam']),
        ([9], ['ts', 'tc']),
        ([10], ['r5', 'scr']),
        ([11], ['dvdrip']),
        ([14], ['brrip']),
        ([12], ['dvdr']),
    ]

    def buildUrl(self, media, quality):
        return (
            tryUrlencode(fireEvent('library.query', media, single = True)),
            self.getCatId(quality)[0]
        )

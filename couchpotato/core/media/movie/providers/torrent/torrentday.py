from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.torrentday import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'TorrentDay'


class TorrentDay(MovieProvider, Base):

    cat_ids = [
        ([11], ['720p', '1080p']),
        ([1, 21, 25], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
        ([3], ['dvdr']),
        ([5], ['bd50']),
    ]

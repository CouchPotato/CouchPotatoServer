from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.torrent.thepiratebay import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'ThePirateBay'


class ThePirateBay(MovieProvider, Base):

    cat_ids = [
        ([209], ['3d']),
        ([207], ['720p', '1080p', 'bd50']),
        ([201], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr']),
        ([201, 207], ['brrip']),
        ([202], ['dvdr'])
    ]

    def buildUrl(self, media, page, cats):
        return (
            tryUrlencode('"%s"' % fireEvent('library.query', media, single = True)),
            page,
            ','.join(str(x) for x in cats)
        )

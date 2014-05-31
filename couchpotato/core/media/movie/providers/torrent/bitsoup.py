from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.bitsoup import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'Bitsoup'


class Bitsoup(MovieProvider, Base):
    cat_ids = [
        ([17], ['3d']),
        ([41], ['720p', '1080p']),
        ([20], ['dvdr']),
        ([19], ['brrip', 'dvdrip']),
    ]
    cat_backup_id = 0

    def buildUrl(self, title, media, quality):
        query = tryUrlencode({
            'search': '"%s" %s' % (title, media['info']['year']),
            'cat': self.getCatId(quality)[0],
        })
        return query

from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.iptorrents import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'IPTorrents'


class IPTorrents(MovieProvider, Base):

    cat_ids = [
        ([87], ['3d']),
        ([48], ['720p', '1080p', 'bd50']),
        ([72], ['cam', 'ts', 'tc', 'r5', 'scr']),
        ([7], ['dvdrip', 'brrip']),
        ([6], ['dvdr']),
    ]

    def buildUrl(self, title, media, quality):
        query = '"%s" %s' % (title.replace(':', ''), media['info']['year'])

        return self._buildUrl(query, quality)

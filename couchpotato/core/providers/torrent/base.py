from couchpotato.core.helpers.variable import getImdb, md5
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import YarrProvider

log = CPLog(__name__)


class TorrentProvider(YarrProvider):

    type = 'torrent'

    def imdbMatch(self, url, imdbId):
        if getImdb(url) == imdbId:
            return True

        if url[:4] == 'http':
            try:
                cache_key = md5(url)
                data = self.getCache(cache_key, url)
            except IOError:
                log.error('Failed to open %s.', url)
                return False

            return getImdb(data) == imdbId

        return False

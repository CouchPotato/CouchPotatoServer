from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider

log = CPLog(__name__)


class KickAssTorrents(TorrentProvider):

    urls = {
        'download': 'http://torrents.thepiratebay.org/%s/%s.torrent',
        'detail': 'http://www.kat.ph/%s-t%s.html',
        'search': 'http://www.kat.ph/%s-i%s/',
    }


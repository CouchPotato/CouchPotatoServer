from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.variable import tryInt, cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
from couchpotato.environment import Env
import re
import time
import traceback
from pprint import pprint

log = CPLog(__name__)


class Yify(TorrentProvider):
   
    urls = {
        'test' : 'https://yify-torrents.com/api',
        'search' : 'https://yify-torrents.com/api/list.json?keywords=%s&quality=%s',
        'detail': 'https://yify-torrents.com/api/movie.json?id=%s'
    }

    http_time_between_calls = 1 #seconds

    def _search(self, movie, quality, results):
        try:
            data = self.getJsonData(self.urls['search'] % (movie['library']['title'], quality['identifier']))
        except:
            log.error('Search on Yify (%s) failed (could not decode JSON)', params)
            return

        if data:
            try:
                for result in data:
                    results.append({
                        'id': result['MovieID'],
                        'name': result['MovieTitle'],
                        'url': result['TorrentUrl'],
                        'detail_url': self.urls['detail'] % result['MovieID'],
                        'size': self.parseSize(result['Size']),
                        'seeders': tryInt(result['TorrentSeeds']),
                        'leechers': tryInt(result['TorrentPeers'])
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))
  

from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.providers.base import MultiProvider
from couchpotato.core.providers.info.base import MovieProvider, SeasonProvider, EpisodeProvider
from couchpotato.core.providers.torrent.base import TorrentProvider

log = CPLog(__name__)


class TorrentDay(MultiProvider):

    def getTypes(self):
        return [Movie, Season, Episode]

class Base(TorrentProvider):

    urls = {
        'test': 'http://www.td.af/',
        'login': 'http://www.td.af/torrents/',
        'login_check': 'http://www.torrentday.com/userdetails.php',
        'detail': 'http://www.td.af/details.php?id=%s',
        'search': 'http://www.td.af/V3/API/API.php',
        'download': 'http://www.td.af/download.php/%s/%s',
    }

    http_time_between_calls = 1 #seconds

    def _search(self, media, quality, results):

        if media['type'] in 'movie':
            q = '"%s %s"' % (fireEvent('searcher.get_search_title', media['library']), media['library']['year'])
        else:
            q = '"%s"' % fireEvent('searcher.get_search_title', media['library'], include_identifier = True)


        params = {
            '/browse.php?': None,
            'cata': 'yes',
            'jxt': 8,
            'jxw': 'b',
            'search': q,
        }

        data = self.getJsonData(self.urls['search'], params = params, opener = self.login_opener)
        try: torrents = data.get('Fs', [])[0].get('Cn', {}).get('torrents', [])
        except: return

        for torrent in torrents:
            results.append({
                'id': torrent['id'],
                'name': torrent['name'],
                'url': self.urls['download'] % (torrent['id'], torrent['fname']),
                'detail_url': self.urls['detail'] % torrent['id'],
                'size': self.parseSize(torrent.get('size')),
                'seeders': tryInt(torrent.get('seed')),
                'leechers': tryInt(torrent.get('leech')),
            })

    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'submit': 'submit',
        })

    def loginSuccess(self, output):
        return 'Password not correct' not in output

    def loginCheckSuccess(self, output):
        return 'logout.php' in output.lower()

class Movie(MovieProvider, Base):

    cat_ids = [
        ([11], ['720p', '1080p']),
        ([1, 21, 25], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
        ([3], ['dvdr']),
        ([5], ['bd50']),
    ]

class Season(SeasonProvider, Base):

    cat_ids = [
        ([14], ['hdtv_sd', 'hdtv_720p', 'webdl_720p', 'webdl_1080p']),
    ]

class Episode(EpisodeProvider, Base):

    cat_ids = [
        ([7], ['hdtv_720p', 'webdl_720p', 'webdl_1080p']),
        ([2], [24], [26], ['hdtv_sd'])
    ]
from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.providers.base import MultiProvider
from couchpotato.core.providers.info.base import EpisodeProvider, SeasonProvider, MovieProvider
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class Bitsoup(MultiProvider):

    def getTypes(self):
        return [Movie, Season, Episode]

class Base(TorrentProvider):

    urls = {
        'test': 'https://www.bitsoup.me/',
        'login' : 'https://www.bitsoup.me/takelogin.php',
        'login_check': 'https://www.bitsoup.me/my.php',
        'search': 'https://www.bitsoup.me/browse.php?%s',
        'baseurl': 'https://www.bitsoup.me/%s',
    }


    http_time_between_calls = 1 #seconds

    def _search(self, media, quality, results):

        url = self.urls['search'] % self.buildUrl(media, quality)
        data = self.getHTMLData(url, opener = self.login_opener)

        if data:
            html = BeautifulSoup(data, "html.parser")

            try:
                result_table = html.find('table', attrs = {'class': 'koptekst'})
                if not result_table or 'nothing found!' in data.lower():
                    return

                entries = result_table.find_all('tr')
                for result in entries[1:]:

                    all_cells = result.find_all('td')

                    torrent = all_cells[1].find('a')
                    download = all_cells[3].find('a')

                    torrent_id = torrent['href']
                    torrent_id = torrent_id.replace('details.php?id=', '')
                    torrent_id = torrent_id.replace('&hit=1', '')

                    torrent_name = torrent.getText()

                    torrent_size = self.parseSize(all_cells[7].getText())
                    torrent_seeders = tryInt(all_cells[9].getText())
                    torrent_leechers = tryInt(all_cells[10].getText())
                    torrent_url = self.urls['baseurl'] % download['href']
                    torrent_detail_url = self.urls['baseurl'] % torrent['href']

                    results.append({
                        'id': torrent_id,
                        'name': torrent_name,
                        'size': torrent_size,
                        'seeders': torrent_seeders,
                        'leechers': torrent_leechers,
                        'url': torrent_url,
                        'detail_url': torrent_detail_url,
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))


    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'ssl': 'yes',
        })


    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess

# Bitsoup Categories
#  Movies
#   Movies/3D - 17 (unused)
#   Movies/DVD-R - 20
#   Movies/Packs - 27 (unused)
#   Movies/XviD - 19
#  The site doesn't have HD Movie caterogies, they bundle HD under x264
#   x264 - 41
#  TV
#   TV-HDx264 - 42
#   TV-Packs - 45
#   TV-SDx264 - 49
#   TV-XVID - 7 (unused)

class Movie(MovieProvider, Base):
    cat_ids = [
        ([41], ['720p', '1080p']),
        ([20], ['dvdr']),
        ([19], ['brrip', 'dvdrip']),
    ]
    cat_backup_id = 0

    def buildUrl(self, media, quality):
        query = tryUrlencode({
            'search': '"%s" %s' % (
                fireEvent('library.title', media['library'], include_year = False, single = True),
                media['library']['year']
            ),
            'cat': self.getCatId(quality['identifier'])[0],
        })
        return query

class Season(SeasonProvider, Base):
    # For season bundles, bitsoup currently only has one category
    def buildUrl(self, media, quality):
        query = tryUrlencode({
            'search': fireEvent('library.title', media['library'], single = True),
            'cat': 45 # TV-Packs Category
        })
        return query

class Episode(EpisodeProvider, Base):
    cat_ids = [
        ([42], ['hdtv_720p', 'webdl_720p', 'webdl_1080p', 'bdrip_1080p', 'bdrip_720p', 'brrip_1080p', 'brrip_720p']),
        ([49], ['hdtv_sd', 'webdl_480p'])
    ]
    cat_backup_id = 0

    def buildUrl(self, media, quality):
        query = tryUrlencode({
            'search': fireEvent('library.title', media['library'], single = True),
            'cat': self.getCatId(quality['identifier'])[0],
        })
        return query

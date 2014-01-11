from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import MultiProvider
from couchpotato.core.providers.info.base import EpisodeProvider, SeasonProvider, MovieProvider
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class TorrentShack(MultiProvider):

    def getTypes(self):
        return [Movie, Season, Episode]

class Base(TorrentProvider):

    urls = {
        'test' : 'https://torrentshack.net/',
        'login' : 'https://torrentshack.net/login.php',
        'login_check': 'https://torrentshack.net/inbox.php',
        'detail' : 'https://torrentshack.net/torrent/%s',
        'search' : 'https://torrentshack.net/torrents.php?action=advanced&searchstr=%s&filter_cat[%d]=1&scene=%s',
        'download' : 'https://torrentshack.net/%s',
    }

    http_time_between_calls = 1 #seconds

    def _search(self, media, quality, results):

        url = self.urls['search'] % self.buildUrl(media, quality)
        data = self.getHTMLData(url, opener = self.login_opener)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'id' : 'torrent_table'})
                if not result_table:
                    return

                entries = result_table.find_all('tr', attrs = {'class' : 'torrent'})

                for result in entries:

                    link = result.find('span', attrs = {'class' : 'torrent_name_link'}).parent
                    url = result.find('td', attrs = {'class' : 'torrent_td'}).find('a')

                    results.append({
                        'id': link['href'].replace('torrents.php?torrentid=', ''),
                        'name': unicode(link.span.string).translate({ord(u'\xad'): None}),
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['download'] % link['href'],
                        'size': self.parseSize(result.find_all('td')[4].string),
                        'seeders': tryInt(result.find_all('td')[6].string),
                        'leechers': tryInt(result.find_all('td')[7].string),
                    })

            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'keeplogged': '1',
            'login': 'Login',
        })

    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess

    def getSceneOnly(self):
        return '1' if self.conf('scene_only') else ''

class Movie(MovieProvider, Base):
    # TorrentShack movie search categories
    #   Movies/x264 - 300
    #   Movies/DVD-R - 350
    #   Movies/XviD - 400
    #   Full Blu-ray - 970
    #
    #   REMUX - 320 (not included)
    #   Movies-HD Pack - 982 (not included)
    #   Movies-SD Pack - 983 (not included)
    cat_ids = [
        ([970], ['bd50']),
        ([300], ['720p', '1080p']),
        ([350], ['dvdr']),
        ([400], ['brrip', 'dvdrip']),
    ]
    cat_backup_id = 400

    def buildUrl(self, media, quality):
        query = (tryUrlencode(fireEvent('library.query', media['library'], single = True)),
                 self.getCatId(quality['identifier'])[0],
                 self.getSceneOnly())
        return query

class Season(SeasonProvider, Base):
    # TorrentShack tv season search categories
    #   TV-SD Pack - 980
    #   TV-HD Pack - 981
    #   Full Blu-ray - 970
    cat_ids = [
        ([980], ['hdtv_sd']),
        ([981], ['hdtv_720p', 'webdl_720p', 'webdl_1080p', 'bdrip_1080p', 'bdrip_720p', 'brrip_1080p', 'brrip_720p']),
        ([970], ['bluray_1080p', 'bluray_720p']),
    ]
    cat_backup_id = 980

    def buildUrl(self, media, quality):
        query = (tryUrlencode(fireEvent('library.query', media['library'], single = True)),
                 self.getCatId(quality['identifier'])[0],
                 self.getSceneOnly())
        return query

class Episode(EpisodeProvider, Base):
    # TorrentShack tv episode search categories
    #   TV/x264-HD - 600
    #   TV/x264-SD - 620
    #   TV/DVDrip - 700
    cat_ids = [
        ([600], ['hdtv_720p', 'webdl_720p', 'webdl_1080p', 'bdrip_1080p', 'bdrip_720p', 'brrip_1080p', 'brrip_720p']),
        ([620], ['hdtv_sd'])
    ]
    cat_backup_id = 620

    def buildUrl(self, media, quality):
        query = (tryUrlencode(fireEvent('library.query', media['library'], single = True)),
                 self.getCatId(quality['identifier'])[0],
                 self.getSceneOnly())
        return query

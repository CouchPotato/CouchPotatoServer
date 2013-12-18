from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.providers.base import MultiProvider
from couchpotato.core.providers.info.base import MovieProvider, SeasonProvider, EpisodeProvider
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)

class TorrentLeech(MultiProvider):

    def getTypes(self):
        return [Movie, Season, Episode]

class Base(TorrentProvider):

    urls = {
        'test' : 'http://www.torrentleech.org/',
        'login' : 'http://www.torrentleech.org/user/account/login/',
        'login_check': 'http://torrentleech.org/user/messages',
        'detail' : 'http://www.torrentleech.org/torrent/%s',
        'search' : 'http://www.torrentleech.org/torrents/browse/index/query/%s/categories/%d',
        'download' : 'http://www.torrentleech.org%s',
    }

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def _search(self, media, quality, results):

        url = self.urls['search'] % self.buildUrl(media, quality)

        data = self.getHTMLData(url, opener = self.login_opener)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'id' : 'torrenttable'})
                if not result_table:
                    return

                entries = result_table.find_all('tr')

                for result in entries[1:]:

                    link = result.find('td', attrs = {'class' : 'name'}).find('a')
                    url = result.find('td', attrs = {'class' : 'quickdownload'}).find('a')
                    details = result.find('td', attrs = {'class' : 'name'}).find('a')

                    results.append({
                        'id': link['href'].replace('/torrent/', ''),
                        'name': link.string,
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['download'] % details['href'],
                        'size': self.parseSize(result.find_all('td')[4].string),
                        'seeders': tryInt(result.find('td', attrs = {'class' : 'seeders'}).string),
                        'leechers': tryInt(result.find('td', attrs = {'class' : 'leechers'}).string),
                    })

            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'remember_me': 'on',
            'login': 'submit',
        })

    def loginSuccess(self, output):
        return '/user/account/logout' in output.lower() or 'welcome back' in output.lower()

    loginCheckSuccess = loginSuccess

class Movie(MovieProvider, Base):

    cat_ids = [
        ([13], ['720p', '1080p']),
        ([8], ['cam']),
        ([9], ['ts', 'tc']),
        ([10], ['r5', 'scr']),
        ([11], ['dvdrip']),
        ([14], ['brrip']),
        ([12], ['dvdr']),
    ]

    def buildUrl(self, media, quality):
        return (tryUrlencode('%s' % fireEvent('library.title', media['library'], condense = True,
                                              single = True)), self.getCatId(quality['identifier'])[0])

class Season(SeasonProvider, Base):

    cat_ids = [
        ([27], ['hdtv_sd', 'hdtv_720p', 'webdl_720p', 'webdl_1080p']),
    ]

    def buildUrl(self, media, quality):
        return (tryUrlencode('%s' % fireEvent('library.title', media['library'], condense = True,
                                              single = True)), self.getCatId(quality['identifier'])[0])

class Episode(EpisodeProvider, Base):

    cat_ids = [
        ([32], ['hdtv_720p', 'webdl_720p', 'webdl_1080p']),
        ([26], ['hdtv_sd'])
    ]

    def buildUrl(self, media, quality):
        return (tryUrlencode('%s' % fireEvent('library.title', media['library'], condense = True,
                                              single = True)), self.getCatId(quality['identifier'])[0])

import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
import six


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://www.morethan.tv/',
        'login': 'https://www.morethan.tv/login.php',
        'login_check': 'https://www.morethan.tv/inbox.php',
        'detail': 'https://www.morethan.tv/torrents.php?torrentid=%s',
        'search': 'https://www.morethan.tv/torrents.php?filter_cat%%5B1%%5D=1&action=advanced&searchstr=%s',
        'download': 'https://www.morethan.tv/%s',
    }

    http_time_between_calls = 1  # Seconds

    def _search(self, media, quality, results):

        url = self.urls['search'] % self.buildUrl(media)
        data = self.getHTMLData(url)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'id': 'torrent_table'})
                if not result_table:
                    return

                entries = result_table.find_all('tr', attrs = {'class': 'torrent'})
                for result in entries:

                    link = result.find('a', attrs = {'dir': 'ltr'})
                    url = result.find('a', attrs = {'title': 'Download'})
                    tds = result.find_all('td')
                    size = tds[5].contents[0].strip('\n ')
                    
                    results.append({
                        'id': link['href'].replace('torrents.php?id=', '').split('&')[0],
                        'name': link.contents[0],
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['download'] % link['href'],
                        'size': self.parseSize(size),
                        'seeders': tryInt(tds[len(tds)-2].string),
                        'leechers': tryInt(tds[len(tds)-1].string),
                    })
            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))


    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'login': 'Log in',
        }

    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess

    def getSceneOnly(self):
        return '1' if self.conf('scene_only') else ''


config = [{
    'name': 'morethantv',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'MoreThanTV',
            'description': '<a href="http://morethan.tv/">MoreThanTV</a>',
            'wizard': True,
            'icon': 'AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAABMLAAATCwAAAAAAAAAAAAAiHaEEIh2hYCIdoaEiHaGaIh2hmCIdoZgiHaGYIh2hmCIdoZgiHaGYIh2hlyIdoZUiHaHAIh2htiIdoUEAAAA$
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'scene_only',
                    'type': 'bool',
                    'default': False,
                    'description': 'Only allow scene releases.'
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]




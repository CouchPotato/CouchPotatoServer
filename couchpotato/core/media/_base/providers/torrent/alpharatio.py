import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
import six


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://alpharatio.cc/',
        'login': 'https://alpharatio.cc/login.php',
        'login_check': 'https://alpharatio.cc/inbox.php',
        'detail': 'https://alpharatio.cc/torrents.php?torrentid=%s',
        'search': 'https://alpharatio.cc/torrents.php?action=advanced&searchstr=%s&scene=%s&filter_cat[%d]=1',
        'download': 'https://alpharatio.cc/%s',
    }

    http_time_between_calls = 1  # Seconds
    login_fail_msg = '</span> attempts remaining.'

    def _search(self, media, quality, results):

        url = self.urls['search'] % self.buildUrl(media, quality)
        cleaned_url = url.replace('%3A', '')
        data = self.getHTMLData(cleaned_url)

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

                    results.append({
                        'id': link['href'].replace('torrents.php?id=', '').split('&')[0],
                        'name': link.contents[0],
                        'url': self.urls['download'] % url['href'],
                        'detail_url': self.urls['download'] % link['href'],
                        'size': self.parseSize(tds[len(tds)-4].string),
                        'seeders': tryInt(tds[len(tds)-2].string),
                        'leechers': tryInt(tds[len(tds)-1].string),
                    })
            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))


    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'keeplogged': '1',
            'login': 'Login',
        }

    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess

    def getSceneOnly(self):
        return '1' if self.conf('scene_only') else ''


config = [{
    'name': 'alpharatio',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'AlphaRatio',
            'description': '<a href="http://alpharatio.cc/" target="_blank">AlphaRatio</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACX0lEQVQ4jbWTX0hTURzHv+fu3umdV9GtOZ3pcllGBomJ9RCmkiWIEJUQET2EMqF86aFeegqLHgoio1ICScoieugPiBlFFmpROUjNIub+NKeba2rqvdvuPKeXDIcsgugHB378fj8+X37fcw5hjOFfgvtTc8o7mdveHWv0+YJ5iWb45SQWi2kc7olCnteoHCGUMqbpejBkO99rPDlW5rjV3FjZkmXU+3SiKK8EkOUVxj2+9bZOe8ebhZxSRTCIQmAES1oLQADKp4EIc8gRFr3t+/SNe0oLelatYM0zO56dqS3fmh4eXkoxIrWvAwXegLta8bymYyak9lyGR7d57eHHtOt7aNaQ0AORU8OEqlg0HURTnXi96cCaK0AYEW0l+MAoQoIp48PHke0JAYwyBkYhameUQ3vz7lTt3NRdKH0ajxgqQMJzAMdBkRVdYgAAEA71G2Z6MnOyvSmSJB/bFblN5DHEsosghf3zZduK+1fdQhyEcKitr+r0B2dMAyPOcmd02oxiC2jUjJaSwbPZpoLJhAA1Ci3hGURRlO0Of8nN9/MNUUXSkrQsFQ4meNORG6/G2O/jGXdZ044OKzg3z3r77TUre81tL1pxirLMWnsoMB00LtfjPLh67/OJH3xRMgiHb96JOCVbxbobRONBQNqScffJ6JE4E2VZFvv6BirbXpkboGcA4eGaDOV73G4LAFBKSWRhNsmqfnHCosG159Lxt++GdgC/XuLD3sH60/fdFxjJBNMDAAVZ8CNfVJxPLzbs/uqa2Lj/0stHkWSDFlwS4FIhRKei3a3VNeS//sa/iZ/B6hMIr7Fq4QAAAABJRU5ErkJggg==',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
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

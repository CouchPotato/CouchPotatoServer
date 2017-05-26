# coding=utf-8
import traceback

from bs4 import BeautifulSoup

from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider

log = CPLog(__name__)


class Base(TorrentProvider):
    urls = {
        'test': 'https://bithumen.be/',
        'login': 'https://bithumen.be/takelogin.php',
        'login_check': 'https://bithumen.be/index.php',
        'detail': 'https://bithumen.be/details.php?id=%s',
        'search': 'https://bithumen.be/browse.php?search=%s',
        'download': 'https://bithumen.be/%s',
    }

    http_time_between_calls = 1  # Seconds

    def _search(self, media, quality, results):
        url = self.urls['search'] % media['info']['imdb']
        data = self.getHTMLData(url)
        if data:
            html = BeautifulSoup(data)
            try:
                result_table = html.find('table', attrs={'id': 'torrenttable'})
                if not result_table:
                    return

                entries = result_table.find_all('tr')
                if len(entries) <= 1:
                    return

                for result in entries[1:]:
                    link = result.find('a', attrs={'title': 'Letöltés'})
                    tds = result.find_all('td')
                    item_id = link['href'].split('/')[1]

                    results.append({
                        'id': item_id,
                        'name': result.find('td', attrs={'align': 'left'}).find('b').string,
                        'url': self.urls['download'] % link['href'],
                        'detail_url': self.urls['detail'] % item_id,
                        'size': self.parseSize(result.find('u').text[:-3] + ' ' + result.find('u').text[-3:]),
                        'seeders': tryInt(tds[len(tds) - 2].string),
                        'leechers': tryInt(tds[len(tds) - 1].string.split(' / ')[0]),
                    })
            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'megjegyez': True
        }

    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'bithumen',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'BitHUmen',
            'description': '<a href="https://bithumen.be/">BitHUmen</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAG1JREFUOI2lk1EOwCAIQx+GK3MKD+2+SAjqNgJfltACVWXCohMdgQlrRHASy/mMRyZUQ08d/WwgXwLbBDfSbcXfKxjISbztwSZQvtbuO9AIKmT3Q3OiGq8TGMiE5eJeE5uNTMgFLnLDbROl+50fPoIrDxMRpbcAAAAASUVORK5CYII=',
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

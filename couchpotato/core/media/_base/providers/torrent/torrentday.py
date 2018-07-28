import re
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider

log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://www.torrentday.com/',
        'login': 'https://www.torrentday.com/t',
        'login_check': 'https://www.torrentday.com/userdetails.php',
        'detail': 'https://www.torrentday.com/details.php?id=%s',
        'search': 'https://www.torrentday.com/t.json?q=%s',
        'download': 'https://www.torrentday.com/download.php/%s/%s.torrent',
    }

    http_time_between_calls = 1  # Seconds

    def loginDownload(self, url = '', nzb_id = ''):
        try:
            if not self.login():
                log.error('Failed downloading from %s', self.getName())
            return self.urlopen(url, headers=self.getRequestHeaders())
        except:
            log.error('Failed downloading from %s: %s', (self.getName(), traceback.format_exc()))

    def _searchOnTitle(self, title, media, quality, results):

        query = '"%s" %s' % (title, media['info']['year'])

        data = {
            'q': query,
        }

        data = self.getJsonData(self.urls['search'] % query, headers = self.getRequestHeaders())

        for torrent in data:
            results.append({
                'id': torrent['t'],
                'name': torrent['name'],
                'url': self.urls['download'] % (torrent['t'], torrent['t']),
                'detail_url': self.urls['detail'] % torrent['t'],
                'size': tryInt(torrent['size']) / (1024 * 1024),
                'seeders': torrent['seeders'],
                'leechers': torrent['leechers'],
            })

    def getRequestHeaders(self):
        return {
            'Cookie': self.conf('cookiesetting') or ''
        }

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'submit.x': 18,
            'submit.y': 11,
            'submit': 'submit',
        }

    def loginSuccess(self, output):
        often = re.search('You tried too often, please wait .*</div>', output)
        if often:
            raise Exception(often.group(0)[:-6].strip())

        return 'Password not correct' not in output

    def loginCheckSuccess(self, output):
        return 'logout.php' in output.lower()


config = [{
    'name': 'torrentday',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'TorrentDay',
            'description': '<a href="https://www.torrentday.com/" target="_blank">TorrentDay</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAC5ElEQVQ4y12TXUgUURTH//fO7Di7foeQJH6gEEEIZZllVohfSG/6UA+RSFAQQj74VA8+Bj30lmAlRVSEvZRfhNhaka5ZUG1paKaW39tq5O6Ou+PM3M4o6m6X+XPPzD3zm/+dcy574r515WfIW8CZBM4YAA5Gc/aQC3yd7oXYEONcsISE5dTDh91HS0t7FEWhBUAeN9ynV/d9qJAgE4AECURAcVsGlCCnly26LMA0IQwTa52dje3d3e3hcPi8qqrrMjcVYI3EHCQZlkFOHBwR2QHh2ASAAIJxWGAQEDxjePhs3527XjJwnb37OHBq0T+Tyyjh+9KnEzNJ7nouc1Q/3A3HGsOvnJy+PSUlj81w2Lny9WuJ6+3AmTjD4HOcrdR2dWXLRQePvyaSLfQOPMPC8mC9iHCsOxSyzJCelzdSXlNzD5ujpb25Wbfc/XXJemTXF4+nnCNq+AMLe50uFfEJTiw4GXSFtiHL0SnIq66+p0kSArqO+eH3RdsAv9+f5vW7L7GICq6rmM8XBCAXlBw90rOyxibn5yzfkg/L09M52/jxqdESaIrBXHYZZbB1GX8cEpySxKIB8S5XcOnvqpli1zuwmrTtoLjw5LOK/eeuWsE4JH5IRPaPZKiKigmPp+5pa+u1aEjIMhEgrRkmi9mgxGUhM7LNJSzOzsE3+cOeExovXOjdytE0LV4zqNZUtV0uZzAGoGkhDH/2YHZiErmv4uyWQnZZWc+hoqL3WzlTExN5hhA8IEwkZWZOxwB++30YG/9GkYCPvqAaHAW5uWPROW86OmqCprUR7z1yZDAGQNuCvkoB/baIKUBWMTYymv+gra3eJNvjXu+B562tFyXqTJ6YuHK8rKwvBmC3vR7cOCPQLWFz8LnfXWUrJo9U19BwMyUlJRjTSMJ2ENxUiGxq9KXQfwqYlnWstvbR5aamG9g0uzM8Q4OFt++3NNixQ2NgYmeN03FOTUv7XVpV9aKisvLl1vN/WVhNc/Fi1NEAAAAASUVORK5CYII=',
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
                    'name': 'cookiesetting',
                    'label': 'Cookies',
                    'default': '',
                    'description': 'Cookies',
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

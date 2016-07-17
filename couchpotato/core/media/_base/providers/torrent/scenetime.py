import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://www.scenetime.com/',
        'login': 'https://www.scenetime.com/takelogin.php',
        'login_check': 'https://www.scenetime.com/inbox.php',
        'detail': 'https://www.scenetime.com/details.php?id=%s',
        'search': 'https://www.scenetime.com/browse.php?search=%s&cat=%d',
        'download': 'https://www.scenetime.com/download.php/%s/%s',
    }

    cat_ids = [
        ([59], ['720p', '1080p']),
        ([81], ['brrip']),
        ([102], ['bd50']),
        ([3], ['dvdrip']),
    ]

    http_time_between_calls = 1  # Seconds
    login_fail_msg = 'Username or password incorrect'
    cat_backup_id = None

    def _searchOnTitle(self, title, movie, quality, results):

        url = self.urls['search'] % (tryUrlencode('%s %s' % (title.replace(':', ''), movie['info']['year'])), self.getCatId(quality)[0])
        data = self.getHTMLData(url)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find(attrs = {'id': 'torrenttable'})

                if not result_table:
                    log.error('failed to generate result_table')
                    return

                entries = result_table.find_all('tr')

                for result in entries[1:]:
                    cells = result.find_all('td')
                    link = result.find('a', attrs = {'class': 'index'})
                    torrent_id = link['href'].replace('download.php/','').split('/')[0]
                    torrent_file = link['href'].replace('download.php/','').split('/')[1]
                    size = self.parseSize(cells[5].contents[0] + cells[5].contents[2])
                    name_row = cells[1].contents[0]
                    name = name_row.getText()
                    seeders_row = cells[6].contents[0]
                    seeders = seeders_row.getText()


                    results.append({
                        'id': torrent_id,
                        'name': name,
                        'url': self.urls['download']  % (torrent_id,torrent_file),
                        'detail_url': self.urls['detail'] % torrent_id,
                        'size': size,
                        'seeders': seeders,
                    })

            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return {
            'login': 'submit',
            'username': self.conf('username'),
            'password': self.conf('password'),
        }

    def loginSuccess(self, output):
        return 'logout.php' in output.lower() or 'Welcome' in output.lower()

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'scenetime',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'SceneTime',
            'description': '<a href="https://www.scenetime.com" target="_blank">SceneTime</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAYdEVYdFNvZnR3YXJlAHBhaW50Lm5ldCA0LjAuNWWFMmUAAAIwSURBVDhPZZFbSBRRGMePs7Mzjma7+9AWWxpeYrXLkrcIfUwIpIeK3tO1hWhfltKwhyJMFIqgCz2EpdHWRun2oGG02O2hlYyypY21CygrlbhRIYHizO6/mdk5szPtB785hzm//zeXj7Q89q4I4QaQBx6ZHQY84Efq4Rrbg4rxVmx61AJ2pFY/twzvhP1hU4ZwIQ8K7mw1wdzdhrrxQ7g8E0Q09R6flubw+mcM7tHWPJcwt91ghuTQUDWYW8rejbrRA3i1OA0xLYGWJO8bxw6q50YIc70CRoQbNbj2MQgpkwsrpTYI7ze5CoS5UgYjpTd3YWphWg1l1CuwLC4jufQNtaG9JleBWM67YKR6oBlzf+bVoPIOUiaNwVgIzcF9sF3aknMvZFfCnnNCp9eJqqsNSKQ+qw2USssNzrzoh9Dnynmaq6yEPe2AkfX9lXjy5akWz9ZkcgqVFz0mj0KsJ0tgROh2oCfSJ3/3ihaHPA0Rh+/7UNhtN7kKhAsI+J+a3u2If49r8WxFZiawtsuR5xLumBUU3s/B2bkOm0+V4V3yrTwFOgcg8SMBe8CmuxTC+SygFB3l8TzxDLOpWYiSqEWzFf0ahc2/RncphPcSUIqPWPFhPqZFcrUqraLzXkA+Z3WXQvh2eaNR3MHmNVB+YPjNMMqPb9Q9I6YGRR0WTMQj6hOV+f/++wuDLwfg7iqH4GVMQQrh28w3Nvgd2H22Hk09jag6UYoSH4/C9gKTo9NG8A8MPUM4DJp74gAAAABJRU5ErkJggg==',
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
                    'default': 20,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]

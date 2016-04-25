import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
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
        'search': 'https://www.morethan.tv/torrents.php?%s&filter_cat%%5B1%%5D=1&action=advanced&searchstr=%s',
        'download': 'https://www.morethan.tv/%s',
    }

    http_time_between_calls = 1  # Seconds
    login_fail_msg = 'You entered an invalid password.'

    def _searchOnTitle(self, title, movie, quality, results):

        movieTitle = tryUrlencode('%s %s' % (title.replace(':', ''), movie['info']['year']))
        url = self.urls['search'] % (self.getSceneOnly(), movieTitle)
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
                    url = result.find('span', attrs = {'title': 'Download'}).parent
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
        return 'releasetype=24' if self.conf('scene_only') else ''


config = [{
    'name': 'morethantv',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'MoreThanTV',
            'description': '<a href="http://morethan.tv/" target="_blank">MoreThanTV</a>',
            'wizard': True,
            'icon': 'AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAABMLAAATCwAAAAAAAAAAAAAiHaEEIh2hYCIdoaEiHaGaIh2hmCIdoZgiHaGYIh2hmCIdoZgiHaGYIh2hlyIdoZUiHaHAIh2htiIdoUEAAAAAIh2hJyIdoW0iHaFsIh2hbCIdoWsiHaFrIh2hayIdoWsiHaFrIh2hayIdoWoiHaFbIh2hsyIdof8iHaH7Ih2hQSIdoQciHaEDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAiHaG8Ih2h/yIdoZgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIh2hoSIdof8iHaGeAAAAAAAAAAAAAAAAIh2hIiIdoZkiHaGZIh2hIiIdoSIiHaGZIh2hiAAAAAAAAAAAAAAAACIdoaEiHaH/Ih2hngAAAAAAAAAAAAAAACIdoaoiHaH/Ih2h/yIdoUQiHaF3Ih2h/yIdof8iHaFEAAAAAAAAAAAiHaGiIh2h/yIdoZ4AAAAAAAAAAAAAAAAiHaG7Ih2h/yIdoREAAAAAIh2h7iIdof8iHaH/Ih2hqgAAAAAAAAAAIh2hoiIdof8iHaGeAAAAAAAAAAAAAAAAIh2huyIdof8AAAAAIh2hVSIdof8iHaGZIh2hzCIdof8iHaERAAAAACIdoaEiHaH/Ih2hngAAAAAAAAAAIh2hZiIdod0iHaH/Ih2hmSIdobsiHaH/Ih2hVSIdoXciHaH/Ih2hdwAAAAAiHaGhIh2h/yIdoZ4AAAAAAAAAACIdoZkiHaH/Ih2h/yIdof8iHaH/Ih2h7gAAAAAiHaEzIh2h/yIdobsAAAAAIh2hoSIdof8iHaGeAAAAAAAAAAAAAAAAIh2huyIdof8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACIdoaEiHaH/Ih2hngAAAAAAAAAAAAAAACIdobsiHaH/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAiHaGhIh2h/yIdoZ4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIh2hoSIdof8iHaGeIh2hCyIdoQYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACIdocUiHaH/Ih2hlSIdoSMiHaFwIh2hfSIdoXEiHaF3Ih2heiIdoXkiHaF5Ih2heSIdoXoiHaFzIh2hYiIdocIiHaH/Ih2h5yIdoS4AAAAAIh2hLyIdoXoiHaGMIh2hcyIdoXMiHaFzIh2hcyIdoXMiHaFyIh2heSIdoY0iHaFsIh2hSSIdoQoAAAAAAAEgNgAAb2Q/+CA1//hTdOA4cGngGCA54hhHZeQIaW7ACG50wIgAUOf4Q0Xn+E9S//hFVj/4PTYAAFJPgAFTUw==',
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

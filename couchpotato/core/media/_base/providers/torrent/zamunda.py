import re
import traceback

import datetime
from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):
    URL = 'http://zamunda.net'

    urls = {
        'test': URL,
        'login': '{}/takelogin.php'.format(URL),
        'login_check': '{}/listing'.format(URL),
        'detail': '{}/details.php?id=%s'.format(URL),
        'search': '{}/listing.php?search=%s&field=name&cat=%s'.format(URL),
        'download': '{}/download.php/%s/download.torrent'.format(URL),
    }

    cat_ids = [
        ([5], ['720p', '1080p']),
        ([19], ['cam']),
        ([19], ['ts', 'tc']),
        ([19], ['r5', 'scr']),
        ([20], ['dvdrip']),
        ([42], ['brrip', 'bd50']),
        ([20], ['dvdr']),
    ]

    http_time_between_calls = 1  # Seconds
    login_fail_msg = 'Username or password incorrect'
    cat_backup_id = None

    def _search(self, movie, quality, results):

        title = movie['title']
        age = 0
        try:
            year = movie['info']['year']
            curryear = datetime.datetime.now().year
            age = curryear - year
        except KeyError:
            log.error('Couldn\'t get movie year')
            year = 0

        url = self.urls['search'] % (title.replace(':', ''), self.getCatId(quality)[0])

        def _fetch(_url):
            data = self.getHTMLData(_url)
            if data:
                html = BeautifulSoup(data)

                try:
                    parent_table = html.find('table', attrs={'class': 'mainouter'})
                    result_table = parent_table.find('table', attrs={'border': '1'})
                    if not result_table:
                        return

                    entries = result_table.find_all('tr')

                    for result in entries[1:]:
                        cells = result.find_all('td')

                        link = cells[1].find('a')

                        full_id_pattern = re.compile("id=([0-9]+)")
                        torrent_id = full_id_pattern.findall(link['href'])[0]
                        try:
                            name = cells[1].select('.fa-download')[0].find_parent('a').attrs['onmouseover'].replace(
                                "Tip('Download: ", '').replace("')", '')
                        except (AttributeError, KeyError):
                            name = '%s - %s' %(title, year)

                        r = {
                            'id': torrent_id,
                            'name': name,
                            'url': self.urls['download'] % torrent_id,
                            'detail_url': self.urls['detail'] % torrent_id,
                            'size': self.parseSize(''.join(cells[5].text)),
                            'seeders': tryInt(cells[7].text),
                            'leechers': tryInt(cells[8].text),
                            'age': age,
                        }

                        results.append(r)
                except AttributeError:
                    log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

                next_el = html.select('.gotonext')
                if next_el and next_el[0].attrs.get('href'):
                    _url = self.URL + next_el[0].attrs.get('href')
                    _fetch(_url)

        _fetch(url)

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'login': 'submit',
        }

    def loginSuccess(self, output):
        return 'Welcome' in output.decode("cp1251")

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'zamunda',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'ZamundaNET',
            'description': '<a href="http://zamunda.net" target="_blank">ZamundaNET</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAACQFBMVEXO0NLS09XT1NbU1dbV09Dc2tbm5OLm5uXu8O/v8fD39vX8/fz8/f/9/f/+/f7+/v3+/v///f7///3///7////09PDs6eb////Y1dLU0s/////////++vP////39/jk39vN0dbNzMr+/fz///75+vrGzNPe5e////7V1tfm5eTr7/P6+vuzv87u7u37+/uww9qmuM2mu9H7+/vO0tfq7/OQrtCovNP09/iatNLE1Obj6vLx9PiStd7Y3+iOrtLt8/eIq9OiwufL2Ojm6/Hs8faOtuTG0+Pb5O7W4OyYtdeHq9Ngm9y/1OxanutJnfxKm/ZKnPhLn/9LoP9Mof9Nof9Oof9Oov9Pov5Po/9QnvRQov9RnfRRovxRo/9Rpf9SpP9Spf9Tne9TpP9UpP9Upf9Vpf9Vpv9Wpf5Wpf9Wpv9Wp/9Xpv5Xpv9Zp/5bp/1bqP9eneNepvZfqv5fqv9gq/9hnuNjoOZjrP5jrP9nrv9pr/9rsP9vsv58uf+Cvf+Gvv+Lwv+Rxf+Uxv+YxPaYyP+ayf6byf6cyv+gzf+jzv+mz/+vzO2z1v+01/610/W12P632v/A3f7A3v/D0+XG4f7I1+rI2OnK2u3L2+3M5P7M5f/O3e/O4/3O5f/P4ffS5//T4vLT5//X6f/Y6v/Y6//Z5vbb5/Tb7f/d7f/f7v/g7v7l7ffl8v/m8f7m8f/n8Pro8Pfo8Pjp8/7q9P/r8fnr9f/u9v/z+Pz3+v/4+//5/P76/P/8/f79/f/9/v7///+JoyvbAAAATnRSTlMAAAAAAAAAAAAAAAAAAAAAAAAAAAABAgIEBRYXGRsiJSYpdHZ5enp6e3t7fH5+fn+Cgpmjo6rIyMvLy8vNzejo6enp6enq6uzv8fT4+fyl89npAAAA/0lEQVQY0wXBS06DQBgA4P+fRxkKCliraX2kwcSVJ3DrBYxXcOuRPILHcO/CxEWNXUhLhRBKw3uYzvh96CInlusL3pa7djCUAaC3eDwKzFC8rRMJ6LLwOQgEAEC9fo0k5dOX+ZSZ92U2s/zFZ8u8W88H+Ppg/OKS3YQVGT9YfQ8ZPe1iAP4kyBkdpN71DqAGXekJEfWhM1FqARJZ5FowlnvdRElXXvtFQxtG58SGjCvJoDLBdvdNiqvlwWlsjWrVrP72JR2B7kRbI4Cj4nL7SxXcZ1IaNIiNlUU/lKn8Lh1TRKRdGm9qtM3xSXg+9IayYpMkgLYxZjYKBOmqOlKI/76FeaAtgS6gAAAAAElFTkSuQmCC',
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

import re
import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.variable import tryInt, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'download': 'https://www.ilovetorrents.me/%s',
        'detail': 'https://www.ilovetorrents.me/%s',
        'search': 'https://www.ilovetorrents.me/browse.php?search=%s&page=%s&cat=%s',
        'test': 'https://www.ilovetorrents.me/',
        'login': 'https://www.ilovetorrents.me/takelogin.php',
        'login_check': 'https://www.ilovetorrents.me'
    }

    cat_ids = [
        (['41'], ['720p', '1080p', 'brrip']),
        (['19'], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr']),
        (['20'], ['dvdr'])
    ]

    cat_backup_id = 200
    disable_provider = False
    http_time_between_calls = 1

    def _searchOnTitle(self, title, movie, quality, results):

        page = 0
        total_pages = 1
        cats = self.getCatId(quality)

        while page < total_pages:

            movieTitle = tryUrlencode('"%s" %s' % (title, movie['info']['year']))
            search_url = self.urls['search'] % (movieTitle, page, cats[0])
            page += 1

            data = self.getHTMLData(search_url)
            if data:
                try:

                    results_table = None

                    data_split = splitString(data, '<table')
                    soup = None
                    for x in data_split:
                        soup = BeautifulSoup(x)
                        results_table = soup.find('table', attrs = {'class': 'koptekst'})
                        if results_table:
                            break

                    if not results_table:
                        return

                    try:
                        pagelinks = soup.findAll(href = re.compile('page'))
                        page_numbers = [int(re.search('page=(?P<page_number>.+'')', i['href']).group('page_number')) for i in pagelinks]
                        total_pages = max(page_numbers)
                    except:
                        pass

                    entries = results_table.find_all('tr')

                    for result in entries[1:]:
                        prelink = result.find(href = re.compile('details.php'))
                        link = prelink['href']
                        download = result.find('a', href = re.compile('download.php'))['href']

                        if link and download:

                            def extra_score(item):
                                trusted = (0, 10)[result.find('img', alt = re.compile('Trusted')) is not None]
                                vip = (0, 20)[result.find('img', alt = re.compile('VIP')) is not None]
                                confirmed = (0, 30)[result.find('img', alt = re.compile('Helpers')) is not None]
                                moderated = (0, 50)[result.find('img', alt = re.compile('Moderator')) is not None]

                                return confirmed + trusted + vip + moderated

                            id = re.search('id=(?P<id>\d+)&', link).group('id')
                            url = self.urls['download'] % download

                            fileSize = self.parseSize(result.select('td.rowhead')[5].text)
                            results.append({
                                'id': id,
                                'name': toUnicode(prelink.find('b').text),
                                'url': url,
                                'detail_url': self.urls['detail'] % link,
                                'size': fileSize,
                                'seeders': tryInt(result.find_all('td')[2].string),
                                'leechers': tryInt(result.find_all('td')[3].string),
                                'extra_score': extra_score,
                                'get_more_info': self.getMoreInfo
                            })

                except:
                    log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'submit': 'Welcome to ILT',
        }

    def getMoreInfo(self, item):
        cache_key = 'ilt.%s' % item['id']
        description = self.getCache(cache_key)

        if not description:

            try:
                full_description = self.getHTMLData(item['detail_url'])
                html = BeautifulSoup(full_description)
                nfo_pre = html.find('td', attrs = {'class': 'main'}).findAll('table')[1]
                description = toUnicode(nfo_pre.text) if nfo_pre else ''
            except:
                log.error('Failed getting more info for %s', item['name'])
                description = ''

            self.setCache(cache_key, description, timeout = 25920000)

        item['description'] = description
        return item

    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'ilovetorrents',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'ILoveTorrents',
            'description': 'Where the Love of Torrents is Born',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAACPUlEQVR4AYWM0U9SbxjH3+v266I/oNvWZTfd2J1d0ZqbZEFwWrUImOKs4YwtumFKZvvlJJADR2TCQQlMPKg5NmpREgaekAPnBATKgmK1LqQlx6awHnZWF1Tr2Xfvvs+7z+dB0mlO7StpAh+M4S/2jbo3w8+xvJvlnSneEt+10zwer5ujNUOoChjALWFw5XOwdCAk/P57cGvPl+Oht0W7VJHN5NC1uW1BON4hGjXbwpVWMZhsy9v7sEIXAsDNYBXgdkEoIKyWD2CF8ut/aOXTZc/fBSgLWw1BgA4BDHOV0GkT90cBQpXahU5TFomsb38XhJC5/Tbh1P8c6rJlBeGfAeyMhUFwNVcs9lxV9Ot0dwmyd+mrNvRtbJ2fSPC6Z3Vsvub2z3sDFACAAYzk0+kUyxEkyfN7PopqNBro55A+P6yPKIrL5zF1HwjdeBJJCObIsZO79bo3sHhWhglo5WMV3mazuVPb4fLvSL8/FAkB1hK6rXQPwYhMyROK8VK5LAiH/jsMt0HQjxiN4/ePdoilllcqDyt3Mkg8mRBNbIhMb8RERkowQA/p76g0/UDDdCoNmDminM0qSK5vlpE5kugCHhNPxntwWmJPYTMZtYcFR6ABHQsVRlYLukVORaaULvqKI46keFSCv77kSPS6kxrPptLNDHgz16fWBtyxe6v5h08LUy+KI8ushqTPWWIX8Sg6b45IrGtyW6zXFb/hpQf9m3oqfWuB0fpSw0uZ4WB69En69uOk2rmO2V52PXj+A/mI4ESKpb2HAAAAAElFTkSuQmCC',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False
                },
                {
                    'name': 'username',
                    'label': 'Username',
                    'type': 'string',
                    'default': '',
                    'description': 'The user name for your ILT account',
                },
                {
                    'name': 'password',
                    'label': 'Password',
                    'type': 'password',
                    'default': '',
                    'description': 'The password for your ILT account.',
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
        }
    ]
}]

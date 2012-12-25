from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.variable import tryInt, possibleTitles, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import ResultList
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
from dateutil.parser import parse
import re
import time

log = CPLog(__name__)


class FTDWorld(NZBProvider):

    urls = {
        'search': 'http://ftdworld.net/category.php?%s',
        'detail': 'http://ftdworld.net/spotinfo.php?id=%s',
        'download': 'http://ftdworld.net/cgi-bin/nzbdown.pl?fileID=%s',
        'login': 'http://ftdworld.net/index.php',
    }

    http_time_between_calls = 3 #seconds

    cat_ids = [
        ([4, 11], ['dvdr']),
        ([1], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
        ([10, 13, 14], ['bd50', '720p', '1080p']),
    ]
    cat_backup_id = 1

    def search(self, movie, quality):

        if self.isDisabled():
            return []

        results = ResultList(self, movie, quality)
        for title in possibleTitles(getTitle(movie['library'])):
            results.extend(self._search(title, movie, quality))

        return results

    def _search(self, title, movie, quality):

        q = '"%s" %s' % (title, movie['library']['year'])

        params = tryUrlencode({
            'ctitle': q,
            'customQuery': 'usr',
            'cage': Env.setting('retention', 'nzb'),
            'csizemin': quality.get('size_min'),
            'csizemax': quality.get('size_max'),
            'ccategory': 14,
            'ctype': ','.join([str(x) for x in self.getCatId(quality['identifier'])]),
        })

        data = self.getHTMLData(self.urls['search'] % params, opener = self.login_opener)

        if data:
            try:

                html = BeautifulSoup(data)
                main_table = html.find('table', attrs = {'id':'ftdresult'})

                if not main_table:
                    return []

                results = ResultList(self, movie, quality)
                items = main_table.find_all('tr', attrs = {'class': re.compile('tcontent')})

                for item in items:
                    tds = item.find_all('td')
                    nzb_id = tryInt(item.attrs['data-spot'])

                    up = item.find('img', attrs = {'src': re.compile('up.png')})
                    down = item.find('img', attrs = {'src': re.compile('down.png')})

                    results.append({
                        'id': nzb_id,
                        'name': toUnicode(item.find('a', attrs = {'href': re.compile('./spotinfo')}).text.strip()),
                        'age': self.calculateAge(int(time.mktime(parse(tds[2].text).timetuple()))),
                        'url': self.urls['download'] % nzb_id,
                        'download': self.loginDownload,
                        'detail_url': self.urls['detail'] % nzb_id,
                        'score': (tryInt(up.attrs['title'].split(' ')[0]) * 3) - (tryInt(down.attrs['title'].split(' ')[0]) * 3) if up else 0,
                    })

            except:
                log.error('Failed to parse HTML response from FTDWorld')

        return results

    def getLoginParams(self):
        return tryUrlencode({
            'userlogin': self.conf('username'),
            'passlogin': self.conf('password'),
            'submit': 'Log In',
        })

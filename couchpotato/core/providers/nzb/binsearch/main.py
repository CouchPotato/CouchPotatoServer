from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
import re
import traceback

log = CPLog(__name__)


class BinSearch(NZBProvider):

    urls = {
        'download': 'https://www.binsearch.info/fcgi/nzb.fcgi?q=%s',
        'detail': 'https://www.binsearch.info%s',
        'search': 'https://www.binsearch.info/index.php?%s',
    }

    http_time_between_calls = 4 # Seconds

    def _search(self, movie, quality, results):

        q = '%s %s' % (movie['library']['identifier'], quality.get('identifier'))
        arguments = tryUrlencode({
            'q': q,
            'm': 'n',
            'max': 250,
            'adv_age': Env.setting('retention', 'nzb'),
            'adv_sort': 'date',
            'adv_col': 'on',
            'adv_nfo': 'on',
            'minsize': quality.get('size_min'),
            'maxsize': quality.get('size_max'),
        })

        data = self.getHTMLData(self.urls['search'] % arguments)

        if data:
            try:

                html = BeautifulSoup(data)
                main_table = html.find('table', attrs = {'id':'r2'})

                if not main_table:
                    return

                items = main_table.find_all('tr')

                for row in items:
                    title = row.find('span', attrs = {'class':'s'})

                    if not title: continue

                    nzb_id = row.find('input', attrs = {'type':'checkbox'})['name']
                    info = row.find('span', attrs = {'class':'d'})
                    size_match = re.search('size:.(?P<size>[0-9\.]+.[GMB]+)', info.text)

                    def extra_check(item):
                        parts = re.search('available:.(?P<parts>\d+)./.(?P<total>\d+)', info.text)
                        total = tryInt(parts.group('total'))
                        parts = tryInt(parts.group('parts'))

                        if (total / parts) < 0.95 or ((total / parts) >= 0.95 and not 'par2' in info.text.lower()):
                            log.info2('Wrong: \'%s\', not complete: %s out of %s', (item['name'], parts, total))
                            return False

                        if 'requires password' in info.text.lower():
                            log.info2('Wrong: \'%s\', passworded', (item['name']))
                            return False

                        return True

                    results.append({
                        'id': nzb_id,
                        'name': title.text,
                        'age': tryInt(re.search('(?P<size>\d+d)', row.find_all('td')[-1:][0].text).group('size')[:-1]),
                        'size': self.parseSize(size_match.group('size')),
                        'url': self.urls['download'] % nzb_id,
                        'detail_url': self.urls['detail'] % info.find('a')['href'],
                        'extra_check': extra_check
                    })

            except:
                log.error('Failed to parse HTML response from BinSearch: %s', traceback.format_exc())

    def download(self, url = '', nzb_id = ''):

        params = {'action': 'nzb'}
        params[nzb_id] = 'on'

        try:
            return self.urlopen(url, params = params, show_error = False)
        except:
            log.error('Failed getting nzb from %s: %s', (self.getName(), traceback.format_exc()))

        return 'try_next'


import re
import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt, simplifyString
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.nzb.base import NZBProvider


log = CPLog(__name__)


class Base(NZBProvider):

    urls = {
        'download': 'https://www.binsearch.info/fcgi/nzb.fcgi?q=%s',
        'detail': 'https://www.binsearch.info%s',
        'search': 'https://www.binsearch.info/index.php?%s',
    }

    http_time_between_calls = 4  # Seconds

    def _search(self, media, quality, results):

        data = self.getHTMLData(self.urls['search'] % self.buildUrl(media, quality))

        if data:
            try:

                html = BeautifulSoup(data)
                main_table = html.find('table', attrs = {'id': 'r2'})

                if not main_table:
                    return

                items = main_table.find_all('tr')

                for row in items:
                    title = row.find('span', attrs = {'class': 's'})

                    if not title: continue

                    nzb_id = row.find('input', attrs = {'type': 'checkbox'})['name']
                    info = row.find('span', attrs = {'class':'d'})
                    size_match = re.search('size:.(?P<size>[0-9\.]+.[GMB]+)', info.text)

                    age = 0
                    try: age = re.search('(?P<size>\d+d)', row.find_all('td')[-1:][0].text).group('size')[:-1]
                    except: pass

                    def extra_check(item):
                        parts = re.search('available:.(?P<parts>\d+)./.(?P<total>\d+)', info.text)
                        total = tryInt(parts.group('total'))
                        parts = tryInt(parts.group('parts'))

                        if (total / parts) < 1 and ((total / parts) < 0.95 or ((total / parts) >= 0.95 and not ('par2' in info.text.lower() or 'pa3' in info.text.lower()))):
                            log.info2('Wrong: \'%s\', not complete: %s out of %s', (item['name'], parts, total))
                            return False

                        if 'requires password' in info.text.lower():
                            log.info2('Wrong: \'%s\', passworded', (item['name']))
                            return False

                        return True

                    results.append({
                        'id': nzb_id,
                        'name': simplifyString(title.text),
                        'age': tryInt(age),
                        'size': self.parseSize(size_match.group('size')),
                        'url': self.urls['download'] % nzb_id,
                        'detail_url': self.urls['detail'] % info.find('a')['href'],
                        'extra_check': extra_check
                    })

            except:
                log.error('Failed to parse HTML response from BinSearch: %s', traceback.format_exc())

    def download(self, url = '', nzb_id = ''):

        data = {
            'action': 'nzb',
            nzb_id: 'on'
        }

        try:
            return self.urlopen(url, data = data, show_error = False)
        except:
            log.error('Failed getting nzb from %s: %s', (self.getName(), traceback.format_exc()))

        return 'try_next'


config = [{
    'name': 'binsearch',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'nzb_providers',
            'name': 'binsearch',
            'description': 'Free provider, less accurate. See <a href="https://www.binsearch.info/">BinSearch</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
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

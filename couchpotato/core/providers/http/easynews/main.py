import os
import requests
import urllib
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.http.base import HTTPProvider

log = CPLog(__name__)


class Easynews(HTTPProvider):

    urls = {
        'search': 'http://members.easynews.com/global5/index.html?fty[]=VIDEO&u=1',
    }

    def _search(self, movie, quality, results):
        """
        defaults = {
            'id': 0,
            'type': self.provider.type,
            'provider': self.provider.getName(),
            'download': self.provider.download,
            'url': '',
            'name': '',
            'age': 0,
            'size': 0,
            'description': '',
            'score': 0
        }
        """
        q = '%s %s %s' % (simplifyString(getTitle(movie['library'])), movie['library']['year'], quality.get('identifier'))
        log.info(q)

        search = []
        r = requests.get(self.urls['search'],
                     params={'gps': q},
                     auth=(self.conf('username'), self.conf('password')))

        soup = BeautifulSoup(r.text)
        rows = soup.find_all('tr', 'rRow1') + soup.find_all('tr', 'rRow2')
        for tr in rows:
            url = tr.find('td', 'subject').find('a')['href']
            search.append({
                'id': tr.find('input', 'checkbox')['value'],
                'file': urllib.unquote(os.path.basename(url)),
                'url': url,
                'size': tr.find('td', 'fSize').string,
                'date': tr.find('td', 'timeStamp').string
            })

        for r in search:

            def extra_score(item):
                group1 = (0, 50)[any(s in r['file'].lower() for s in ('ctrlhd', 'wiki', 'esir', 'shitsony', 'cytsunee', 'don.mkv'))]
                group2 = (0, 30)[any(s in r['file'].lower() for s in ('chd', 'hdc', 'hdchina'))]
                hires = (0, 10)['1080p' in r['file'].lower()]

                return group1 + group2 + hires

            d = parser.parse(r['date'])
            if d > datetime.now():
                d = datetime(d.year - 1, d.month, d.day)
            age = (datetime.now() - d).days + 1

            results.append({
                'id': r['id'],
                'name': r['file'],
                'age': age,
                'size': self.parseSize(r['size']),
                'url': r['url'],
                'detail_url': self.urls['search'] + '&gps=%s' % q,
                'extra_score': extra_score
            })

    def download(self, url='', nzb_id=''):
        pass

import os
import requests
import urllib
from bs4 import BeautifulSoup
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
        r = requests.get('http://members.easynews.com/global5/index.html?fty[]=VIDEO&u=1',
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
                'size': tr.find('td', 'fSize').string
            })

        for r in search:
            results.append({
                'id': r['id'],
                'name': r['file'],
                'age': 1,  # @todo
                'size': self.parseSize(r['size']),
                'url': r['url'],
            })

    def download(self, url='', nzb_id=''):
        pass

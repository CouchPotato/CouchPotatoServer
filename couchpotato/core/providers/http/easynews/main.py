import os
import requests
import urllib
from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.http.base import HTTPProvider

log = CPLog(__name__)


class Easynews(HTTPProvider, RSS):

    def search(self, movie, quality):

        results = []

        if self.isDisabled():
            return results

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
            new = {
                'id': r['id'],
                'type': 'nzb',
                'provider': self.getName(),
                'name': r['file'],
                'age': 1,  # @todo
                'size': self.parseSize(r['size']),
                'url': r['url'],
                'download': self.download,
                'detail_url': '',
                'description': '',
                'check_nzb': False,
            }

            is_correct_movie = fireEvent('searcher.correct_movie',
                                         nzb=new, movie=movie, quality=quality,
                                         imdb_results=False, single=True)

            if is_correct_movie:
                new['score'] = fireEvent('score.calculate', new, movie, single=True)
                results.append(new)
                self.found(new)

        return results

    def download(self, url='', nzb_id=''):
        pass

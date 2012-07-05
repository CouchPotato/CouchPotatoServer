from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
from urllib import quote_plus
import traceback
import urllib

log = CPLog(__name__)


class SceneAccess(TorrentProvider):

    urls = {
        'test': 'https://www.sceneaccess.eu/',
        'login' : 'https://www.sceneaccess.eu/login',
        'detail': 'https://www.sceneaccess.eu/details?id=%s',
        'search': 'https://www.sceneaccess.eu/browse?method=2&c%d=%d',
        'download': 'https://www.sceneaccess.eu/%s',
    }

    cat_ids = [
        ([22], ['720p', '1080p']),
        ([7], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
        ([8], ['dvdr']),
    ]

    http_time_between_calls = 1 #seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        q = '"%s %s" %s' % (simplifyString(getTitle(movie['library'])), movie['library']['year'], quality.get('identifier'))
        arguments = tryUrlencode({
            'search': q,
        })
        url = "%s&%s" % (self.urls['search'], arguments)
        url = url % (
           self.getCatId(quality['identifier'])[0],
           self.getCatId(quality['identifier'])[0]
        )

        # Do login for the cookies
        if not self.login_opener and not self.login():
            return results

        cache_key = 'sceneaccess.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
        data = self.getCache(cache_key, url, opener = self.login_opener)

        if data:
            html = BeautifulSoup(data)

            try:
                resultsTable = html.find('table', attrs = {'id' : 'torrents-table'})
                entries = resultsTable.findAll('tr', attrs = {'class' : 'tt_row'})
                for result in entries:

                    link = result.find('td', attrs = {'class' : 'ttr_name'}).find('a')
                    url = result.find('td', attrs = {'class' : 'td_dl'}).find('a')
                    leechers = result.find('td', attrs = {'class' : 'ttr_leechers'}).find('a')

                    new = {
                        'id': link['href'].replace('details?id=', ''),
                        'type': 'torrent',
                        'check_nzb': False,
                        'description': '',
                        'provider': self.getName(),
                        'name': link['title'],
                        'url': self.urls['download'] % url['href'],
                        'size': self.parseSize(result.find('td', attrs = {'class' : 'ttr_size'}).contents[0]),
                        'seeders': tryInt(result.find('td', attrs = {'class' : 'ttr_seeders'}).find('a').string),
                        'leechers': tryInt(leechers.string) if leechers else 0,
                        'download': self.download,
                    }

                    imdb_results = self.imdbMatch(self.urls['detail'] % new['id'], movie['library']['identifier'])

                    new['score'] = fireEvent('score.calculate', new, movie, single = True)
                    is_correct_movie = fireEvent('searcher.correct_movie', nzb = new, movie = movie, quality = quality,
                                                     imdb_results = imdb_results, single_category = False, single = True)

                    if is_correct_movie:
                        results.append(new)
                        self.found(new)

                return results
            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

        return []

    def getLoginParams(self, params):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'submit': 'come on in',
        })

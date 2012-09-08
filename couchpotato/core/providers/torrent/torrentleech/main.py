from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
from urllib import quote_plus
import traceback


log = CPLog(__name__)


class TorrentLeech(TorrentProvider):

    urls = {
        'test' : 'http://torrentleech.org/',
        'login' : 'http://torrentleech.org/user/account/login/',
        'detail' : 'http://torrentleech.org/torrent/%s',
        'search' : 'http://torrentleech.org/torrents/browse/index/query/%s/categories/%d',
        'download' : 'http://torrentleech.org%s',
    }

    cat_ids = [
        ([13], ['720p', '1080p']),
        ([8], ['cam']),
        ([9], ['ts', 'tc']),
        ([10], ['r5', 'scr']),
        ([11], ['dvdrip']),
        ([14], ['brrip']),
        ([12], ['dvdr']),
    ]

    http_time_between_calls = 1 #seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        # Cookie login
        if not self.login_opener and not self.login():
            return results

        cache_key = 'torrentleech.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
        url = self.urls['search'] % (quote_plus(getTitle(movie['library']).replace(':', '') + ' ' + quality['identifier']), self.getCatId(quality['identifier'])[0])
        data = self.getCache(cache_key, url, opener = self.login_opener)

        if data:
            html = BeautifulSoup(data)

            try:
                result_table = html.find('table', attrs = {'id' : 'torrenttable'})
                if not result_table:
                    return results

                entries = result_table.find_all('tr')

                for result in entries[1:]:

                    link = result.find('td', attrs = {'class' : 'name'}).find('a')
                    url = result.find('td', attrs = {'class' : 'quickdownload'}).find('a')

                    new = {
                        'id': link['href'].replace('/torrent/', ''),
                        'name': link.string,
                        'type': 'torrent',
                        'check_nzb': False,
                        'description': '',
                        'provider': self.getName(),
                        'url': self.urls['download'] % url['href'],
                        'download': self.loginDownload,
                        'size': self.parseSize(result.find_all('td')[4].string),
                        'seeders': tryInt(result.find('td', attrs = {'class' : 'seeders'}).string),
                        'leechers': tryInt(result.find('td', attrs = {'class' : 'leechers'}).string),
                    }

                    imdb_results = self.imdbMatch(self.urls['detail'] % new['id'], movie['library']['identifier'])

                    new['score'] = fireEvent('score.calculate', new, movie, single = True)
                    is_correct_movie = fireEvent('searcher.correct_movie', nzb = new, movie = movie, quality = quality,
                                                    imdb_results = imdb_results, single = True)

                    if is_correct_movie:
                        results.append(new)
                        self.found(new)

                return results
            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

        return []

    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'remember_me': 'on',
            'login': 'submit',
        })

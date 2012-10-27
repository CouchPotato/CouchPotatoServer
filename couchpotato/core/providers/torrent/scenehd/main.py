from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class SceneHD(TorrentProvider):

    urls = {
        'test': 'https://scenehd.org/',
        'login' : 'https://scenehd.org/takelogin.php',
        'detail': 'https://scenehd.org/details.php?id=%s',
        'search': 'https://scenehd.org/browse.php?ajax',
        'download': 'https://scenehd.org/download.php?id=%s',
    }

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

        # Cookie login
        if not self.login_opener and not self.login():
            return results

        cache_key = 'scenehd.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
        data = self.getCache(cache_key, url, opener = self.login_opener)

        if data:
            html = BeautifulSoup(data)

            try:
                resultsTable = html.find_all('table')[6]
                entries = resultsTable.find_all('tr')
                for result in entries[1:]:

                    all_cells = result.find_all('td')

                    detail_link = all_cells[2].find('a')
                    details = detail_link['href']
                    id = details.replace('details.php?id=', '')

                    leechers = all_cells[11].find('a')
                    if leechers:
                        leechers = leechers.string
                    else:
                        leechers = all_cells[11].string

                    new = {
                        'id': id,
                        'name': detail_link['title'],
                        'type': 'torrent',
                        'check_nzb': False,
                        'description': '',
                        'provider': self.getName(),
                        'size': self.parseSize(all_cells[7].string),
                        'seeders': tryInt(all_cells[10].find('a').string),
                        'leechers': tryInt(leechers),
                        'url': self.urls['download'] % id,
                        'download': self.loginDownload,
                    }

                    imdb_link = all_cells[1].find('a')
                    imdb_results = self.imdbMatch(imdb_link['href'], movie['library']['identifier']) if imdb_link else False

                    new['score'] = fireEvent('score.calculate', new, movie, single = True)
                    is_correct_movie = fireEvent('searcher.correct_movie', nzb = new, movie = movie, quality = quality,
                                                     imdb_results = imdb_results, single = True)

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
            'ssl': 'yes',
        })

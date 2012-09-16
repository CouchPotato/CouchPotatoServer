from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
from urlparse import parse_qs
import re
import traceback

log = CPLog(__name__)


class PublicHD(TorrentProvider):

    urls = {
        'test': 'http://publichd.eu',
        'detail': 'http://publichd.eu/index.php?page=torrent-details&id=%s',
        'search': 'http://publichd.eu/index.php',
    }
    http_time_between_calls = 0

    def search(self, movie, quality):

        results = []

        if self.isDisabled() or not quality.get('hd', False):
            return results

        params = tryUrlencode({
            'page':'torrents',
            'search': '%s %s' % (getTitle(movie['library']), movie['library']['year']),
            'active': 1,
        })
        url = '%s?%s' % (self.urls['search'], params)

        cache_key = 'publichd.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
        data = self.getCache(cache_key, url)

        if data:

            try:
                soup = BeautifulSoup(data)

                results_table = soup.find('table', attrs = {'id': 'bgtorrlist2'})
                entries = results_table.find_all('tr')

                for result in entries[2:len(entries) - 1]:
                    info_url = result.find(href = re.compile('torrent-details'))
                    download = result.find(href = re.compile('magnet:'))

                    if info_url and download:

                        url = parse_qs(info_url['href'])

                        new = {
                            'id': url['id'][0],
                            'name': info_url.string,
                            'type': 'torrent_magnet',
                            'check_nzb': False,
                            'description': '',
                            'provider': self.getName(),
                            'url': download['href'],
                            'detail_url': self.urls['detail'] % url['id'][0],
                            'size': self.parseSize(result.find_all('td')[7].string),
                            'seeders': tryInt(result.find_all('td')[4].string),
                            'leechers': tryInt(result.find_all('td')[5].string),
                            'get_more_info': self.getMoreInfo
                        }

                        new['score'] = fireEvent('score.calculate', new, movie, single = True)
                        is_correct_movie = fireEvent('searcher.correct_movie', nzb = new, movie = movie, quality = quality,
                                                        imdb_results = False, single = True)

                        if is_correct_movie:
                            results.append(new)
                            self.found(new)

                return results

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

        return []

    def getMoreInfo(self, item):
        full_description = self.getCache('publichd.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('div', attrs = {'id':'torrmain'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

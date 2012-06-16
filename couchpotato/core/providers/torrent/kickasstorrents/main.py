from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import tryInt, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import StringIO
import gzip
import re
import traceback

log = CPLog(__name__)


class KickAssTorrents(TorrentProvider):

    urls = {
        'test': 'http://www.kat.ph/',
        'detail': 'http://www.kat.ph/%s-t%s.html',
        'search': 'http://www.kat.ph/%s-i%s/',
        'download': 'http://torcache.net/',
    }

    cat_ids = [
        (['cam'], ['cam']),
        (['telesync'], ['ts', 'tc']),
        (['screener', 'tvrip'], ['screener']),
        (['x264', '720p', '1080p', 'blu-ray', 'hdrip'], ['bd50', '1080p', '720p', 'brrip']),
        (['dvdrip'], ['dvdrip']),
        (['dvd'], ['dvdr']),
    ]

    http_time_between_calls = 1 #seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        cache_key = 'kickasstorrents.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
        data = self.getCache(cache_key, self.urls['search'] % (getTitle(movie['library']), movie['library']['identifier'].replace('tt', '')))
        if data:

            cat_ids = self.getCatId(quality['identifier'])
            table_order = ['name', 'size', None, 'age', 'seeds', 'leechers']

            try:
                html = BeautifulSoup(data)
                resultdiv = html.find('div', attrs = {'class':'tabs'})
                for result in resultdiv.find_all('div', recursive = False):
                    if result.get('id').lower() not in cat_ids:
                        continue

                    try:

                        try:
                            for temp in result.find_all('tr'):
                                if temp['class'] is 'firstr' or not temp.get('id'):
                                    continue

                                new = {
                                    'type': 'torrent',
                                    'check_nzb': False,
                                    'description': '',
                                    'provider': self.getName(),
                                    'download': self.download,
                                    'score': 0,
                                }

                                nr = 0
                                for td in temp.find_all('td'):
                                    column_name = table_order[nr]
                                    if column_name:

                                        if column_name is 'name':
                                            link = td.find('div', {'class': 'torrentname'}).find_all('a')[1]
                                            new['id'] = temp.get('id')[-8:]
                                            new['name'] = link.text
                                            new['url'] = td.find_all('a', 'idownload')[1]['href']
                                            if new['url'][:2] == '//':
                                                new['url'] = 'http:%s' % new['url']
                                            new['score'] = 20 if td.find('a', 'iverif') else 0
                                        elif column_name is 'size':
                                            new['size'] = self.parseSize(td.text)
                                        elif column_name is 'age':
                                            new['age'] = self.ageToDays(td.text)
                                        elif column_name is 'seeds':
                                            new['seeds'] = tryInt(td.text)
                                        elif column_name is 'leechers':
                                            new['leechers'] = tryInt(td.text)

                                    nr += 1

                                new['score'] += fireEvent('score.calculate', new, movie, single = True)
                                is_correct_movie = fireEvent('searcher.correct_movie',
                                                                nzb = new, movie = movie, quality = quality,
                                                                imdb_results = True, single_category = False, single = True)
                                if is_correct_movie:
                                    results.append(new)
                                    self.found(new)
                        except:
                            log.error('Failed parsing KickAssTorrents: %s', traceback.format_exc())
                    except:
                        pass

                return results
            except AttributeError:
                log.debug('No search results found.')

        return results

    def ageToDays(self, age_str):
        age = 0
        age_str = age_str.replace('&nbsp;', ' ')

        regex = '(\d*.?\d+).(sec|hour|day|week|month|year)+'
        matches = re.findall(regex, age_str)
        for match in matches:
            nr, size = match
            mult = 1
            if size == 'week':
                mult = 7
            elif size == 'month':
                mult = 30.5
            elif size == 'year':
                mult = 365

            age += tryInt(nr) * mult

        return tryInt(age)

    def download(self, url = '', nzb_id = ''):
        compressed_data = self.urlopen(url = url, headers = {'Referer': 'http://kat.ph/'})

        compressedstream = StringIO.StringIO(compressed_data)
        gzipper = gzip.GzipFile(fileobj = compressedstream)
        data = gzipper.read()

        return data


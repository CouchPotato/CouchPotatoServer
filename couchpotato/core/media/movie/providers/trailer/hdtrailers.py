from string import digits, ascii_letters
import re

from bs4 import SoupStrainer, BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import mergeDicts, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.trailer.base import TrailerProvider
from requests import HTTPError


log = CPLog(__name__)

autoload = 'HDTrailers'


class HDTrailers(TrailerProvider):

    urls = {
        'api': 'http://www.hd-trailers.net/movie/%s/',
        'backup': 'http://www.hd-trailers.net/blog/',
    }
    providers = ['apple.ico', 'yahoo.ico', 'moviefone.ico', 'myspace.ico', 'favicon.ico']
    only_tables_tags = SoupStrainer('table')

    def search(self, group):

        movie_name = getTitle(group)

        url = self.urls['api'] % self.movieUrlName(movie_name)
        try:
            data = self.getCache('hdtrailers.%s' % group['identifier'], url, show_error = False)
        except HTTPError:
            log.debug('No page found for: %s', movie_name)
            data = None

        result_data = {'480p': [], '720p': [], '1080p': []}

        if not data:
            return result_data

        did_alternative = False
        for provider in self.providers:
            results = self.findByProvider(data, provider)

            # Find alternative
            if results.get('404') and not did_alternative:
                results = self.findViaAlternative(group)
                did_alternative = True

            result_data = mergeDicts(result_data, results)

        return result_data

    def findViaAlternative(self, group):
        results = {'480p': [], '720p': [], '1080p': []}

        movie_name = getTitle(group)

        url = "%s?%s" % (self.urls['backup'], tryUrlencode({'s':movie_name}))
        try:
            data = self.getCache('hdtrailers.alt.%s' % group['identifier'], url, show_error = False)
        except HTTPError:
            log.debug('No alternative page found for: %s', movie_name)
            data = None

        if not data:
            return results

        try:
            html = BeautifulSoup(data, 'html.parser', parse_only = self.only_tables_tags)
            result_table = html.find_all('h2', text = re.compile(movie_name))

            for h2 in result_table:
                if 'trailer' in h2.lower():
                    parent = h2.parent.parent.parent
                    trailerLinks = parent.find_all('a', text = re.compile('480p|720p|1080p'))
                    try:
                        for trailer in trailerLinks:
                            results[trailer].insert(0, trailer.parent['href'])
                    except:
                        pass

        except AttributeError:
            log.debug('No trailers found in via alternative.')

        return results

    def findByProvider(self, data, provider):

        results = {'480p':[], '720p':[], '1080p':[]}
        try:
            html = BeautifulSoup(data, 'html.parser', parse_only = self.only_tables_tags)
            result_table = html.find('table', attrs = {'class':'bottomTable'})

            for tr in result_table.find_all('tr'):
                trtext = str(tr).lower()
                if 'clips' in trtext:
                    break

                if 'trailer' in trtext and not 'clip' in trtext and provider in trtext and not '3d' in trtext:
                    if 'trailer' not in tr.find('span', 'standardTrailerName').text.lower():
                        continue
                    resolutions = tr.find_all('td', attrs = {'class':'bottomTableResolution'})
                    for res in resolutions:
                        if res.a and str(res.a.contents[0]) in results:
                            results[str(res.a.contents[0])].insert(0, res.a['href'])

        except AttributeError:
            log.debug('No trailers found in provider %s.', provider)
            results['404'] = True

        return results

    def movieUrlName(self, string):
        safe_chars = ascii_letters + digits + ' '
        r = ''.join([char if char in safe_chars else ' ' for char in string])
        name = re.sub('\s+' , '-', r).lower()

        try:
            int(name)
            return '-' + name
        except:
            return name

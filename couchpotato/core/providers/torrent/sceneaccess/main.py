from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import tryInt, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import StringIO
import gzip
import re
import traceback
import urllib
import urllib2
import cookielib
from urllib import quote_plus
from urllib2 import URLError

log = CPLog(__name__)


class SceneAccess(TorrentProvider):

    urls = {
        'test': 'https://www.sceneaccess.eu/',
        'login' : 'https://www.sceneaccess.eu/login',
        'detail': 'https://www.sceneaccess.eu/details?id=%s',
        'search': 'https://www.sceneaccess.eu/browse?search=%s&method=2&c%d=%d',
        'download': 'https://www.sceneaccess.eu/%s',
    }

    cat_ids = [
        ([22], ['720p', '1080p']),
        ([7], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
        ([8], ['dvdr']),
    ]

    http_time_between_calls = 1 #seconds
    
    def getLoginParams(self):
        loginParams = urllib.urlencode(dict(username=''+self.conf('username'), password=''+self.conf('password'), submit='come on in'))
        return loginParams

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        cache_key = 'sceneaccess.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
        searchUrl =  self.urls['search'] % (quote_plus(getTitle(movie['library']).replace(':','') + ' ' + quality['identifier']), self.getCatId(quality['identifier'])[0], self.getCatId(quality['identifier'])[0])
        loginParams = self.getLoginParams()

        opener = self.login(params = loginParams)
        if not opener:
            log.info("Couldn't login at SceneAccess")
            return results

        data = self.getCache(cache_key, searchUrl)

        if data:
            html = BeautifulSoup(data)
        
        else:
            log.info("No results found at SceneAccess")

        try:
            resultsTable = html.find('table', attrs = {'id' : 'torrents-table'})            
            entries = resultsTable.findAll('tr', attrs = {'class' : 'tt_row'})
            for result in entries:
                new = {
                    'type': 'torrent',
                    'check_nzb': False,
                    'description': '',
                    'provider': self.getName(),
                }
                
                link = result.find('td', attrs = {'class' : 'ttr_name'}).find('a')
                new['name'] = link['title']
                new['id'] = link['href'].replace('details?id=', '')
                url = result.find('td', attrs = {'class' : 'td_dl'}).find('a')
                new['url'] = self.urls['download'] % url['href']
                new['size'] = self.parseSize(result.find('td', attrs = {'class' : 'ttr_size'}).contents[0])
                new['seeders'] = int(result.find('td', attrs = {'class' : 'ttr_seeders'}).find('a').string)
                leechers = result.find('td', attrs = {'class' : 'ttr_leechers'}).find('a')
                if leechers:
                    new['leechers'] = int(leechers.string)
                else:
                    new['leechers'] = 0
            
                new['imdbid'] = movie['library']['identifier']
                new['extra_score'] = self.extra_score
                new['score'] = fireEvent('score.calculate', new, movie, single = True)
                is_correct_movie = fireEvent('searcher.correct_movie', nzb = new, movie = movie, quality = quality,
                                                 imdb_results = True, single_category = False, single = True)

                if is_correct_movie:
                    new['download'] = self.download
                    results.append(new)
                    self.found(new)
            return results
        
        except: 
            log.info("No results found at SceneAccess")
            return []

    def extra_score(self, nzb):
        url = self.urls['detail'] % nzb['id']
        imdbId = nzb['imdbid']
        return self.imdbMatch(url, imdbId)

    def imdbMatch(self, url, imdbId):
        try:
            data = urllib2.urlopen(url).read()
            pass
        except IOError:
            log.error('Failed to open %s.' % url)
            return ''

        html = BeautifulSoup(data)
        imdbDiv = html.find('span', attrs = {'class':'i_link'})
        imdbDiv = str(imdbDiv).decode("utf-8", "replace")
        imdbIdAlt = re.sub('tt[0]*', 'tt', imdbId)

        if 'imdb.com/title/' + imdbId in imdbDiv or 'imdb.com/title/' + imdbIdAlt in imdbDiv:
            return 50
        return 0

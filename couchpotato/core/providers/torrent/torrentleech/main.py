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
import sys


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
    
    def getLoginParams(self):
        loginParams = urllib.urlencode(dict(username=''+self.conf('username'), password=''+self.conf('password'), remember_me='on', login='submit'))
	return loginParams

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        cache_key = 'torrentleech.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
        searchUrl =  self.urls['search'] % (quote_plus(getTitle(movie['library']).replace(':','') + ' ' + quality['identifier']), self.getCatId(quality['identifier'])[0])
        loginParams = self.getLoginParams()
      
        opener = self.login(params = loginParams)
        if not opener:
            log.info("Couldn't login at Torrentleech")
            return results

        data = self.getCache(cache_key, searchUrl)

        if data:
            html = BeautifulSoup(data)
        
        else:
            log.info("No results found at Torrentleech")

        try:
            resultsTable = html.find('table', attrs = {'id' : 'torrenttable'})            
            entries = resultsTable.findAll('tr')
            for result in entries[1:]:
                new = {
                    'type': 'torrent',
                    'check_nzb': False,
                    'description': '',
                    'provider': self.getName(),
                }
                
                link = result.find('td', attrs = {'class' : 'name'}).find('a')
                new['name'] = link.string
                new['id'] = link['href'].replace('/torrent/', '')
                url = result.find('td', attrs = {'class' : 'quickdownload'}).find('a')
                new['url'] = self.urls['download'] % url['href']
                new['size'] = self.parseSize(result.findAll('td')[4].string)
                new['seeders'] = int(result.find('td', attrs = {'class' : 'seeders'}).string)
                new['leechers'] = int(result.find('td', attrs = {'class' : 'leechers'}).string)                
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
            log.info("No results found at TorrentLeech")
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

        imdbIdAlt = re.sub('tt[0]*', 'tt', imdbId)
        data = unicode(data, errors='ignore')
        if 'imdb.com/title/' + imdbId in data or 'imdb.com/title/' + imdbIdAlt in data:
            return 50
        return 0

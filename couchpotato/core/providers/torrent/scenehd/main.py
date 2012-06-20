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


class SceneHD(TorrentProvider):

    urls = {
        'test': 'http://scenehd.org/',
        'detail': 'http://scenehd.org/details.php?id=%s',
        'search': 'http://scenehd.org/browse.php?ajax&search=%s',
        'download': 'http://scenehd.org/download.php?id=%s',
    }
   
    http_time_between_calls = 1 #seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        cache_key = 'scenehd.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
        searchUrl =  self.urls['search'] % (quote_plus(getTitle(movie['library']) + ' ' + quality['identifier']))
        data = self.getCache(cache_key, searchUrl)

        if data:
	    
	    try:
	        cookiejar = cookielib.CookieJar()
	        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
	        urllib2.install_opener(opener)
	        params = urllib.urlencode(dict(username=''+self.conf('username'), password=''+self.conf('password'), ssl='yes'))
	        f = opener.open('http://scenehd.org/takelogin.php', params)
	        data = f.read()
	        f.close()
	        f = opener.open(searchUrl)
	        data = f.read()
	        f.close()
            
	    except (IOError, URLError):
                log.error('Failed to open %s.' % url)
	        return results

        html = BeautifulSoup(data)
	
	try:
	    resultsTable = html.findAll('table')[6]
	    entries = resultsTable.findAll('tr')
	    for result in entries[1:]:
	        new = {
	            'type': 'torrent',
                    'check_nzb': False,
                    'description': '',
                    'provider': self.getName(),
                }

	        allCells = result.findAll('td')
	        new['size'] = self.parseSize(allCells[7].string.replace('GiB', 'GB'))
                new['seeders'] = allCells[10].find('a').string
	        leechers = allCells[11].find('a')
	        if leechers:
	            new['leechers'] = leechers.string
                else:
	            new['leechers'] = allCells[11].string
	       
	        detailLink = allCells[2].find('a')
	        details = detailLink['href']
	        new['id'] = details.replace('details.php?id=', '')
	        new['name'] = detailLink['title']
	    
	        imdbLink = allCells[1].find('a')
	        if imdbLink:
	            new['imdbresult'] = imdbLink['href'].replace('http://www.imdb.com/title/','').rstrip('/')
	        else:
	            new['imdbresult'] = 'tt00000000'
	       
	        new['url'] = self.urls['download'] % new['id']
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
	    log.info("No results found at SceneHD")
	    return []

    def extra_score(self, nzb):
        imdbIdAlt = re.sub('tt[0]*', 'tt', nzb['imdbresult'])
        if nzb['imdbresult'] == nzb['imdbid'] or imdbIdAlt == nzb['imdbid']:
	    return 50
        return 0

    def download(self, url = '', nzb_id = ''):
        torrent = self.urlopen(url)
        return torrent



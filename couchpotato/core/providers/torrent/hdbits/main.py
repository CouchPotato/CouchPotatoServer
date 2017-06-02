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
import json

log = CPLog(__name__)


class HDBits(TorrentProvider):

    urls = {
        'test': 'https://hdbits.org/',
        'detail': 'https://hdbits.org/details.php?id=%s&source=browse',
        'search': 'https://hdbits.org/browse2.php#film/dir=null&searchtype=film&actorfilm=film&search=%s',
    }
    regex =  ''
    http_time_between_calls = 1 #seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        cache_key = 'hdbits.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
	searchUrl =  self.urls['search'] % movie['library']['identifier']
        data = self.getCache(cache_key, searchUrl)

	if data:
	    
	    try:
	        # Grabs the hidden value (name=lol) from the login page, logs in and saves the cookie
	        loginPage = self.urlopen('https://hdbits.org/login.php')
		html = BeautifulSoup(loginPage)
                loginCode = html.find('input', attrs = {'name':'lol'})['value']
	        cookiejar = cookielib.CookieJar()
	        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
	        urllib2.install_opener(opener)
	        params = urllib.urlencode(dict(uname=''+self.conf('username'), password=''+self.conf('password'), lol=loginCode))
	        f = opener.open('https://hdbits.org/takelogon.php', params)
	        data = f.read()
	        f.close()
	       
	        # Posts an ajax search based on the imdb id of the movie
		imdbShortened = re.sub('tt[0]*', 'tt', movie['library']['identifier'])
		imdbShortened = imdbShortened.replace('tt', '')
		paramsimdb = urllib.urlencode(dict(searchtype='classic', imdb=imdbShortened, filmexpand=1))
		f = opener.open('https://hdbits.org/ajax/search.php', paramsimdb)
		data = f.read()
		jsondata = json.loads(data)
		f.close()
		for result in jsondata['results']:
                    new = {
	                'type': 'torrent',
                        'check_nzb': False,
                        'description': '',
                        'provider': self.getName(),
			'url' : 'https://hdbits.org/download.php/' + result['filename'] + '?id=' + result['id'] + '&passkey=' + self.conf('passkey'),
			'name' : getTitle(movie['library']) + ' ' + result['name'],
			'id' : result['id'],
			'seeds' : result['seeders'],
			'leechers' : result['leechers'],
			'size' : (int(result['size'])/(1024*1024)),
                    }
		    new['score'] = fireEvent('score.calculate', new, movie, single = True)
		  
		    # Add 50 to the score for having a perfect imdb match.
		    new['score'] += 50

		    is_correct_movie = fireEvent('searcher.correct_movie', nzb = new, movie = movie, quality = quality,
		                                    imdb_results = True, single_category = False, single = True)
		    if is_correct_movie:
		        new['download'] = self.download
		        results.append(new)
		        self.found(new)
                return results
	    except (IOError, URLError):
                log.error('Failed to open %s.' % url)
	        return results

    def download(self, url = '', nzb_id = ''):
        torrent = self.urlopen(url)
        return torrent
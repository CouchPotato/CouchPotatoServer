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


class TorrentLeech(TorrentProvider):

    urls = {
        'test': 'http://torrentleech.org/',
        'detail': 'http://torrentleech.org/torrent/%s',
        'search': 'http://torrentleech.org/torrents/browse/index/query/%s/categories/%d',
    }

    regex = '<span class="title"><a href="\/torrent\/(?P<id>.*?)">(?P<title>.*?)</a></span>.+?<a href="(?P<url>.*?)">.+?comments">.+?<td>(?P<size>.*?)([MB,GB])</td>'

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

        cache_key = 'torrentleech.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
	searchUrl =  self.urls['search'] % (quote_plus(getTitle(movie['library']) + ' ' + quality['identifier']), self.getCatId(quality['identifier'])[0])
        data = self.getCache(cache_key, searchUrl)

	if data:

            cat_ids = self.getCatId(quality['identifier'])
	    
	    try:
	        cookiejar = cookielib.CookieJar()
	        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
	        urllib2.install_opener(opener)
	        params = urllib.urlencode(dict(username=''+self.conf('username'), password=''+self.conf('password'), remember_me='on', login='submit'))
	        f = opener.open('http://torrentleech.org/user/account/login/', params)
	        data = f.read()
	        f.close()
	        f = opener.open(searchUrl)
	        data = f.read()
	        f.close()
            
	    except (IOError, URLError):
                log.error('Failed to open %s.' % url)
	        return results

        match = re.compile(self.regex, re.DOTALL ).finditer(data)

        for torrent in match:
	    new = {
	         'type': 'torrent',
                 'check_nzb': False,
                 'description': '',
                 'provider': self.getName(),
            }

	    new['url'] = 'http://torrentleech.org' + torrent.group('url')
	    new['name'] = torrent.group('title')
	    new['id'] = torrent.group('id')
	    new['seeds'] = 100
	    new['leechers'] = 1
	    new['size'] = self.parseSize(torrent.group('size') + 'B')
	    new['score'] = fireEvent('score.calculate', new, movie, single = True)
	    new['score'] += self.imdbMatch(self.urls['detail'] % new['id'], movie['library']['identifier'])
	    is_correct_movie = fireEvent('searcher.correct_movie', nzb = new, movie = movie, quality = quality,
                                   imdb_results = True, single_category = False, single = True)

            if is_correct_movie:
	        new['download'] = self.download
                results.append(new)
                self.found(new)
        return results

    def imdbMatch(self, url, imdbId):
        try:
            data = urllib2.urlopen(url).read()
            pass
        except IOError:
            log.error('Failed to open %s.' % url)
            return ''

	imdbIdAlt = re.sub('tt[0]*', 'tt', imdbId)

	if 'imdb.com/title/' + imdbId in data or 'imdb.com/title/' + imdbIdAlt in data:
	        return 50
	return 0

    def download(self, url = '', nzb_id = ''):
        torrent = self.urlopen(url)
        return torrent



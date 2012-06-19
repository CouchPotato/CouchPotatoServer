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
        'detail': 'https://www.sceneaccess.eu/details?id=%s',
        'search': 'https://www.sceneaccess.eu/browse?search=%s&method=2&c%d=%d',
        'download': 'https://www.sceneaccess.eu/download/%d/%s/%s.torrent',
    }

    regex = '<td class="ttr_name"><a href="details\?id=(?P<id>.*?)".+?<b>(?P<title>.*?)</b>.+?href="(?P<url>.*?)".*?</td>.+?<td class="ttr_size">(?P<size>.*?)<br />'

    cat_ids = [
        ([22], ['720p', '1080p']),
        ([7], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
        ([8], ['dvdr']),
    ]

    http_time_between_calls = 1 #seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        cache_key = 'sceneaccess.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
	searchUrl =  self.urls['search'] % (quote_plus(getTitle(movie['library']) + ' ' + quality['identifier']), self.getCatId(quality['identifier'])[0], self.getCatId(quality['identifier'])[0])
        data = self.getCache(cache_key, searchUrl)

	if data:

            cat_ids = self.getCatId(quality['identifier'])
	    
	    try:
	        cookiejar = cookielib.CookieJar()
	        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
	        urllib2.install_opener(opener)
	        params = urllib.urlencode(dict(username=''+self.conf('username'), password=''+self.conf('password'), submit='come on in'))
	        f = opener.open('https://www.sceneaccess.eu/login', params)
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

	    new['url'] = 'https://www.sceneaccess.eu/' + torrent.group('url')
	    new['name'] = torrent.group('title')
	    new['size'] = self.parseSize(torrent.group('size'))
	    new['id'] = torrent.group('id')
	    new['seeds'] = 100
	    new['leechers'] = 1
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

	html = BeautifulSoup(data)
        imdbDiv = html.find('span', attrs = {'class':'i_link'})
        imdbDiv = str(imdbDiv).decode("utf-8", "replace")
	imdbIdAlt = re.sub('tt[0]*', 'tt', imdbId)

	if 'imdb.com/title/' + imdbId in imdbDiv or 'imdb.com/title/' + imdbIdAlt in imdbDiv:
	        return 50
	return 0

    def download(self, url = '', nzb_id = ''):
        torrent = self.urlopen(url)
        return torrent



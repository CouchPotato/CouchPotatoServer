from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getTitle, getImdb, tryInt, cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
from couchpotato.environment import Env
from dateutil.parser import parse
import os
import time
import re
import htmlentitydefs
import urllib
import urllib2
import cookielib
import json


log = CPLog(__name__)


class PassThePopcorn(TorrentProvider):

    urls = {
         'detail': '%s/torrent/%s',
         'search': '%s/search/%s/0/7/%d'
    }

    disable_provider = False
    
    domain = 'tls.passthepopcorn.me'

    opener = None
    cookiejar = None
    quality_search_params = {
        '1080p':    {'resolution': '1080p'},
        '720p':     {'resolution': '720p'},
        'brrip':    {'media': 'Blu-ray'}, # results are filtered by post_search_filters to narrow down the search
        'dvdr':     {'resolution': 'anysd'}, # results are filtered by post_search_filters to narrow down the search
        'dvdrip':   {'media': 'DVD'}, # results are filtered by post_search_filters to narrow down the search
        'scr':      {'media': 'DVD-Screener'},
        'r5':       {'media': 'R5'},
        'tc':       {'media': 'TC'},
        'ts':       {'media': 'TS'},
        'cam':      {'media': 'CAM'}
    }
    
    post_search_filters = {
        '1080p':    {'Resolution': ['1080p']},
        '720p':     {'Resolution': ['720p']},
        'brrip':    {'Source': ['Blu-ray'], 'Quality': ['High Definition'], 'Container': ['!ISO']},
        'dvdr':     {'Codec': ['DVD5', 'DVD9']},
        'dvdrip':   {'Source': ['DVD'], 'Codec': ['!DVD5', '!DVD9']},
        'scr':      {'Source': ['DVD-Screener']},
        'r5':       {'Source': ['R5']},
        'tc':       {'Source': ['TC']},
        'ts':       {'Source': ['TS']},
        'cam':      {'Source': ['CAM']}
    }
    
    
    
    class NotLoggedInHTTPError(urllib2.HTTPError):
        def __init__(self, url, code, msg, headers, fp):
            urllib2.HTTPError.__init__(self, url, code, msg, headers, fp)
    
    class PTPHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            log.debug("302 detected; redirected to %s" % headers['Location'])
            if (headers['Location'] != 'login.php'):
                #log.info("Redirect NOT due to not being logged in detected; allowing redirect")
                return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
            else:
                #log.info("NotLoggedInHTTPError detected; raising it")
                raise PassThePopcorn.NotLoggedInHTTPError(req.get_full_url(), code, msg, headers, fp)
    

    def __init__(self):
        cookieprocessor = urllib2.HTTPCookieProcessor(self.cookiejar)
        self.cookiejar = cookielib.CookieJar()
        self.opener = urllib2.build_opener(cookieprocessor, PassThePopcorn.PTPHTTPRedirectHandler())
        self.opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.75 Safari/537.1'),
            ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
            ('Accept-Language', 'en-gb,en;q=0.5'),
            ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
            ('Keep-Alive', '115'),
            ('Connection', 'keep-alive'),
            ('Cache-Control', 'max-age=0'),
        ]
	self.domain = self.conf('domain') if self.conf('domain') else self.domain
        super(PassThePopcorn, self).__init__()

    def login(self):
        log.info("Trying to log into passthepopcorn.me...")
        url = 'https://%s/login.php' % (self.domain)
        postdata = urllib.urlencode({'username': self.conf('username'), 'password': self.conf('password'), 'keeplogged': '1', 'login': 'Login'})
        try:
            response = self.opener.open(url, postdata)
            log.debug('Login POST did not throw exception')
        except urllib2.URLError as e:
            log.error('Login to passthepopcorn failed: %s' % e)
            return False
        if response.getcode() == 200:
            log.info('Login HTTP status 200; seems successful')
            return True
        else:
            log.error('Login to passthepopcorn failed: returned code %d' % response.getcode())
            return False
    
    def protected_request(self, url):
        log.debug('Retrieving %s' % url)
        maxattempts = 3
        while maxattempts > 0:
            try:
                response = self.opener.open(url)
                txt = response.read()
                #log.info('Response was:\n %s' % jsontxt)
                if response.getcode() != 200:
                    log.error('Retrieving \'%s\' resulted in HTTP response code %d' % (url, response.getcode()))
                    return None
                return txt
            except PassThePopcorn.NotLoggedInHTTPError as e:
                if not self.login(): # if we can login, just retry
                    log.error('Login failed, could not execute request %s' % url)
                    return None
                log.debug("Should now be logged into passthepopcorn.me, trying request again...")
            except urllib2.URLError as e:
                log.error('Retrieving JSON from url %s failed: %s' % (url, e))
                return None
            maxattempts = maxattempts - 1
    
    def json_request(self, path, params):
        url = 'https://%s/%s?json=noredirect&%s' % (self.domain, path, urllib.urlencode(params))
        txt = self.protected_request(url)
        if txt:
            return json.loads(txt)
        else:
            return None
        
    def enabled(self):
        return  (not self.isDisabled() and \
                self.conf('username') and \
                self.conf('password'))
 
    def torrent_meets_quality_spec(self, torrent, quality):
        if not quality in self.post_search_filters:
            return True
        for field, specs in self.post_search_filters[quality].items():
            matchesOne = False
            seenOne = False
            if not field in torrent:
                log.info('Torrent with ID %s has no field "%s"; cannot apply post-search-filter for quality "%s"' % (torrent['Id'], field, quality))
                continue
            for spec in specs:
                if len(spec) > 0 and spec[0] == '!':
                    # a negative rule; if the field matches, return False
                    if torrent[field] == spec[1:]:
                        return False
                else:
                    # a positive rule; if any of the possible positive values match the field, return True
                    seenOne = True
                    if torrent[field] == spec:
                        matchesOne = True
            if seenOne and not matchesOne:
                return False
        return True
        
    def htmltounicode(self, text):
        def fixup(m):
            text = m.group(0)
            if text[:2] == "&#":
                # character reference
                try:
                    if text[:3] == "&#x":
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text # leave as is
        return re.sub("&#?\w+;", fixup, u'%s' % text)
    
    def unicodetoascii(self, text):
        import unicodedata
        return ''.join(c for c in unicodedata.normalize('NFKD', text) if unicodedata.category(c) != 'Mn')
    
    def htmltoascii(self, text):
        return self.unicodetoascii(self.htmltounicode(text))

    def download(self, url = '', nzb_id = ''):
        return self.protected_request(url)

    def search(self, movie, quality):
        movieTitle = getTitle(movie['library'])
        qualityID = quality['identifier']
        imdbID = movie['library']['info']['imdb']
        movieYear = movie['library']['info']['year']
        
        log.info('Searching for %s' % movieTitle)
        if not self.enabled():
            log.info('PTP not enabled, skipping search')
            return []
        
        params = []
        if qualityID:
            params = self.quality_search_params[qualityID]
        if imdbID:
            params['searchstr'] = imdbID
        else:
            params['searchstr'] = movieTitle
            params['year'] = movieYear
        
        params['order_by'] = 'relevance'
        params['order_way'] = 'descending'
        
        res = self.json_request('torrents.php', params)
        if not res:
            log.error('Search on passthepopcorn.me (%s) failed' % params)
            return []
        
        #log.info('JSON: %s' % json.dumps(res))        
        
        if not 'Movies' in res:
            return []
        results = []
        for ptpmovie in res['Movies']:
            if not 'Torrents' in ptpmovie:
                continue
            for torrent in ptpmovie['Torrents']:
                if not self.torrent_meets_quality_spec(torrent, type):
                    continue
                torrentdesc = '%s %s %s' % (torrent['Resolution'], torrent['Source'], torrent['Codec'])
                if 'GoldenPopcorn' in torrent and torrent['GoldenPopcorn']:
                    torrentdesc += ' HQ'
                if 'Scene' in torrent and torrent['Scene']:
                    torrentdesc += ' Scene'
                if 'RemasterTitle' in torrent and torrent['RemasterTitle']:
                    # eliminate odd characters...
                    torrentdesc += self.htmltoascii(' %s')
                new = {
                    'id': int(torrent['Id']),
                    'type': 'torrent',
                    'name': re.sub('[^A-Za-z0-9\-_ ]+', '', '%s - %s - %s' % (self.htmltoascii(ptpmovie['Title']), ptpmovie['Year'], torrentdesc)),
                    'check_nzb': False,
                    'description': '',
                    'date': int(time.mktime(parse(torrent['UploadTime']).timetuple())),
                    'size': int(torrent['Size']) / (1024*1024),
                    'provider': self.getName(),
                    'seeders': int(torrent['Seeders']),
                    'leechers': int(torrent['Leechers']),
                    'ptpobj': self,
                    'torrentjson': torrent,
                    'extra_score': (lambda torrent: (50 if torrent['torrentjson']['GoldenPopcorn'] else 0)),
                    'download': self.download,
                }
                new['url'] = 'https://%s/torrents.php?action=download&id=%d' % (self.domain, new['id'])
                new['score'] = fireEvent('score.calculate', new, movie, single = True)
                if fireEvent('searcher.correct_movie', nzb = new, movie = movie, quality = quality):
                    results.append(new)
                    self.found(new)
        if not results:
            log.info("Found nothing for '%s'" % movie.name)
        return results

    def getMoreInfo(self, item):
        return {}

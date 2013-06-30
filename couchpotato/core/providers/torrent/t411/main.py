from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.helpers.variable import getTitle, mergeDicts
from couchpotato.core.providers.torrent.base import TorrentProvider
from couchpotato.core.helpers import namer_check
from dateutil.parser import parse
import cookielib
import htmlentitydefs
import json
import re
import time
import traceback
import urllib2
import urllib
import unicodedata

log = CPLog(__name__)


class t411(TorrentProvider):

    urls = {
        'test': 'http://www.t411.me/',
        'detail': 'http://www.t411.me/torrents/?id=%s',
        'search': 'http://www.t411.me/torrents/search/?',
    }

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    class NotLoggedInHTTPError(urllib2.HTTPError):
        def __init__(self, url, code, msg, headers, fp):
            urllib2.HTTPError.__init__(self, url, code, msg, headers, fp)

    class PTPHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            log.debug("302 detected; redirected to %s" % headers['Location'])
            if (headers['Location'] != 'login.php'):
                return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
            else:
                raise t411.NotLoggedInHTTPError(req.get_full_url(), code, msg, headers, fp)

    def getSearchParams(self, movie, quality):
        results = []
        MovieTitles = movie['library']['info']['titles']
        moviequality = simplifyString(quality['identifier'])
        for MovieTitle in MovieTitles:
            try:
                TitleStringReal = str(MovieTitle.encode("latin-1").replace('-',' '))
            except:
                TitleStringReal = str(MovieTitle.encode("utf-8").replace('-',' '))
            if moviequality in ['720p']:
                results.append(urllib.urlencode( {'search': TitleStringReal, 'cat' : 210, 'submit' : 'Recherche', 'subcat': 631 } ) + "&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B7%5D%5B%5D=15")
                results.append(urllib.urlencode( {'search': simplifyString(TitleStringReal), 'cat' : 210, 'submit' : 'Recherche', 'subcat': 631 } ) + "&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B7%5D%5B%5D=15")
            elif moviequality in ['1080p']:
                results.append(urllib.urlencode( {'search': TitleStringReal, 'cat' : 210, 'submit' : 'Recherche', 'subcat': 631 } ) + "&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B7%5D%5B%5D=16")
                results.append(urllib.urlencode( {'search': simplifyString(TitleStringReal), 'cat' : 210, 'submit' : 'Recherche', 'subcat': 631 } ) + "&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B7%5D%5B%5D=16")
            elif moviequality in ['dvd-r']:
                results.append(urllib.urlencode( {'search': TitleStringReal, 'cat' : 210, 'submit' : 'Recherche', 'subcat': 631 } ) + "&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B7%5D%5B%5D=13&term%5B7%5D%5B%5D=14")
                results.append(urllib.urlencode( {'search': simplifyString(TitleStringReal), 'cat' : 210, 'submit' : 'Recherche', 'subcat': 631 } ) + "&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B7%5D%5B%5D=13&term%5B7%5D%5B%5D=14")
            elif moviequality in ['br-disk']:
                results.append(urllib.urlencode( {'search': TitleStringReal, 'cat' : 210, 'submit' : 'Recherche', 'subcat': 631 } ) + "&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B7%5D%5B%5D=17")
                results.append(urllib.urlencode( {'search': simplifyString(TitleStringReal), 'cat' : 210, 'submit' : 'Recherche', 'subcat': 631 } ) + "&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B7%5D%5B%5D=17")
            else:
                results.append(urllib.urlencode( {'search': TitleStringReal, 'cat' : 210, 'submit' : 'Recherche', 'subcat': 631 } ) + "&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B7%5D%5B%5D=8&term%5B7%5D%5B%5D=9&term%5B7%5D%5B%5D=10")
                results.append(urllib.urlencode( {'search': simplifyString(TitleStringReal), 'cat' : 210, 'submit' : 'Recherche', 'subcat': 631 } ) + "&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B7%5D%5B%5D=8&term%5B7%5D%5B%5D=9&term%5B7%5D%5B%5D=10")
            
        return results
    
    def _search(self, movie, quality, results):

        # Cookie login
        if not self.login_opener and not self.login():
            return
        searchStrings= self.getSearchParams(movie,quality)
        for searchString in searchStrings:
            URL = self.urls['search']+searchString
                
            data = self.getHTMLData(URL , opener = self.login_opener)
    
            if data:
    
                cat_ids = self.getCatId(quality['identifier'])
                table_order = ['name', 'size', None, 'age', 'seeds', 'leechers']
    
                try:
                    html = BeautifulSoup(data)
    
                    resultdiv = html.find('table', attrs = {'class':'results'}).find('tbody')
    
                    for result in resultdiv.find_all('tr', recursive = False):
    
                        try:
    
                            categorie = result.find_all('td')[0].find_all('img')[0]['class']                        
                            insert = 0
                        
                            if categorie == ['cat-631']:
                                insert = 1
                            if categorie == ['cat-455']:
                                insert = 1
                         
                            if insert == 1 :
                         
                                new = {}
        
                                idt = result.find_all('td')[2].find_all('a')[0]['href'][1:].replace('torrents/nfo/?id=','')
                                name = result.find_all('td')[1].find_all('a')[0]['title']
                                testname=namer_check.correctName(name,movie)
                                if testname==0:
                                    continue
                                url = ('http://www.t411.me/torrents/download/?id=%s' % idt)
                                detail_url = ('http://www.t411.me/torrents/?id=%s' % idt)
    
                                size = result.find_all('td')[5].text
                                age = result.find_all('td')[4].text
                                seeder = result.find_all('td')[7].text
                                leecher = result.find_all('td')[8].text
        
                                def extra_check(item):
                                    return True
        
                                new['id'] = idt
                                new['name'] = name + ' french'
                                new['url'] = url
                                new['detail_url'] = detail_url
                                new['size'] = self.parseSize(size)
                                new['age'] = self.ageToDays(age)
                                new['seeders'] = tryInt(seeder)
                                new['leechers'] = tryInt(leecher)
                                new['extra_check'] = extra_check
                                new['download'] = self.loginDownload
        
                                results.append(new)
    
                        except:
                            log.error('Failed parsing T411: %s', traceback.format_exc())
    
                except AttributeError:
                    log.debug('No search results found.')
            else:
                log.debug('No search results found.')

    def ageToDays(self, age_str):
        age = 0
        age_str = age_str.replace('&nbsp;', ' ')

        regex = '(\d*.?\d+).(sec|heure|jour|semaine|mois|ans)+'
        matches = re.findall(regex, age_str)
        for match in matches:
            nr, size = match
            mult = 1
            if size == 'semaine':
                mult = 7
            elif size == 'mois':
                mult = 30.5
            elif size == 'ans':
                mult = 365

            age += tryInt(nr) * mult

        return tryInt(age)

    def login(self):

        cookieprocessor = urllib2.HTTPCookieProcessor(cookielib.CookieJar())
        opener = urllib2.build_opener(cookieprocessor, t411.PTPHTTPRedirectHandler())
        opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko)'),
            ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
            ('Accept-Language', 'fr-fr,fr;q=0.5'),
            ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
            ('Keep-Alive', '115'),
            ('Connection', 'keep-alive'),
            ('Cache-Control', 'max-age=0'),
        ]

        try:
            response = opener.open('http://www.t411.me/users/login/', self.getLoginParams())
        except urllib2.URLError as e:
            log.error('Login to T411 failed: %s' % e)
            return False

        if response.getcode() == 200:
            log.debug('Login HTTP T411 status 200; seems successful')
            self.login_opener = opener
            return True
        else:
            log.error('Login to T411 failed: returned code %d' % response.getcode())
            return False

    def getLoginParams(self):
        return tryUrlencode({
             'login': self.conf('username'),
             'password': self.conf('password'),
             'remember': '1',
             'url': '/'
        })
        
        
    def download(self, url = '', nzb_id = ''):
        if not self.login_opener and not self.login():
            return
        
        try:
            return self.urlopen(url, opener = self.login_opener)
        except:
            log.error('Failed getting nzb from %s: %s', (self.getName(), traceback.format_exc()))

        return 'try_next'
        

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from couchpotato.core.helpers import namer_check
import cookielib
import re
import traceback
import urllib2
import urllib
from StringIO import StringIO
import gzip
import time
log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'http://www.t411.io/',
        'detail': 'http://www.t411.io/torrents/?id=%s',
        'search': 'http://www.t411.io/torrents/search/?',
    }

    http_time_between_calls = 1 #seconds
    cat_backup_id = None
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

    class NotLoggedInHTTPError(urllib2.HTTPError):
        def __init__(self, url, code, msg, headers, fp):
            urllib2.HTTPError.__init__(self, url, code, msg, headers, fp)

    class PTPHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            log.debug("302 detected; redirected to %s" % headers['Location'])
            if (headers['Location'] != 'login.php'):
                return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
            else:
                raise Base.NotLoggedInHTTPError(req.get_full_url(), code, msg, headers, fp)

    def getSearchParams(self, movie, quality):
        results = []
        MovieTitles = movie['info']['titles']
        moviequality = simplifyString(quality['identifier'])
        moviegenre = movie['info']['genres']
        if 'Animation' in moviegenre:
            subcat=455
        elif 'Documentaire' in moviegenre or 'Documentary' in moviegenre:
            subcat=634
        else:    
            subcat=631
        if moviequality in ['720p']:
            qualpar="&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B17%5D%5B%5D=1160&term%5B17%5D%5B%5D=722&term%5B7%5D%5B%5D=15&term%5B7%5D%5B%5D=12&term%5B7%5D%5B%5D=1175"
        elif moviequality in ['1080p']:
            qualpar="&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B17%5D%5B%5D=1160&term%5B17%5D%5B%5D=722&term%5B7%5D%5B%5D=16&term%5B7%5D%5B%5D=1162&term%5B7%5D%5B%5D=1174"
        elif moviequality in ['dvd-r','dvdr']:
            qualpar="&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B17%5D%5B%5D=1160&term%5B17%5D%5B%5D=722&term%5B7%5D%5B%5D=13&term%5B7%5D%5B%5D=14"
        elif moviequality in ['br-disk']:
            qualpar="&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B17%5D%5B%5D=1160&term%5B17%5D%5B%5D=722&term%5B7%5D%5B%5D=1171&term%5B7%5D%5B%5D=17"
        else:
            qualpar="&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542&term%5B17%5D%5B%5D=719&term%5B17%5D%5B%5D=1160&term%5B17%5D%5B%5D=722&term%5B7%5D%5B%5D=8&term%5B7%5D%5B%5D=9&term%5B7%5D%5B%5D=10&term%5B7%5D%5B%5D=11&term%5B7%5D%5B%5D=18&term%5B7%5D%5B%5D=19"
        if quality['custom']['3d']==1:
            qualpar=qualpar+"&term%5B9%5D%5B%5D=24&term%5B9%5D%5B%5D=23"
            
        for MovieTitle in MovieTitles:
            try:
                TitleStringReal = str(MovieTitle.encode("latin-1").replace('-',' '))
            except:
                continue
            try:
                results.append(urllib.urlencode( {'search': TitleStringReal, 'cat' : 210, 'submit' : 'Recherche', 'subcat': subcat } ) + qualpar)
                results.append(urllib.urlencode( {'search': simplifyString(unicode(TitleStringReal,"latin-1")), 'cat' : 210, 'submit' : 'Recherche', 'subcat': subcat } ) + qualpar)
            except:
                continue
        
        return results
    
    def _search(self, movie, quality, results):

        # Cookie login
        if not self.last_login_check and not self.login():
            return
        searchStrings= self.getSearchParams(movie,quality)
        lastsearch=0
        for searchString in searchStrings:
            actualtime=int(time.time())
            if actualtime-lastsearch<10:
                timetosleep= 10-(actualtime-lastsearch)
                time.sleep(timetosleep)
            URL = self.urls['search']+searchString
                
            r = self.opener.open(URL)   
            soup = BeautifulSoup( r, "html.parser" )
            if soup.find('table', attrs = {'class':'results'}):
                resultdiv = soup.find('table', attrs = {'class':'results'}).find('tbody')
            else:
                continue
            if resultdiv:
                try:   
                    for result in resultdiv.findAll('tr'):
                        try:
                            categorie = result.findAll('td')[0].findAll('a')[0]['href'][result.findAll('td')[0].findAll('a')[0]['href'].find('='):]
                            insert = 0
                        
                            if categorie == '=631':
                                insert = 1
                            if categorie == '=455':
                                insert = 1
                            if categorie == '=634':
                                insert = 1
                         
                            if insert == 1 :
                         
                                new = {}
        
                                idt = result.findAll('td')[2].findAll('a')[0]['href'][1:].replace('torrents/nfo/?id=','')
                                name = result.findAll('td')[1].findAll('a')[0]['title']
                                testname=namer_check.correctName(name,movie)
                                if testname==0:
                                    continue
                                url = ('http://www.t411.io/torrents/download/?id=%s' % idt)
                                detail_url = ('http://www.t411.io/torrents/?id=%s' % idt)
                                leecher = result.findAll('td')[8].text
                                size = result.findAll('td')[5].text
                                age = result.findAll('td')[4].text
                                seeder = result.findAll('td')[7].text
        
                                def extra_check(item):
                                    return True
        
                                new['id'] = idt
                                new['name'] = name + ' french'
                                new['url'] = url
                                new['detail_url'] = detail_url
                                new['size'] = self.parseSize(str(size))
                                new['age'] = self.ageToDays(str(age))
                                new['seeders'] = tryInt(seeder)
                                new['leechers'] = tryInt(leecher)
                                new['extra_check'] = extra_check
                                new['download'] = self.download
        
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
        regex = '(\d*.?\d+).(sec|heure|heures|jour|jours|semaine|semaines|mois|ans|an)+'
        matches = re.findall(regex, age_str)
        for match in matches:
            nr, size = match
            mult = 0
            if size in ('jour','jours'):
                mult = 1
            if size in ('semaine','semaines'):
                mult = 7
            elif size == 'mois':
                mult = 30
            elif size in ('ans','an'):
                mult = 365

            age += tryInt(nr) * mult

        return tryInt(age)

    def login(self):

        self.opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko)'),
            ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
            ('Accept-Language', 'fr-fr,fr;q=0.5'),
            ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
            ('Keep-Alive', '115'),
            ('Connection', 'keep-alive'),
            ('Cache-Control', 'max-age=0'),
        ]

        try:
            response = self.opener.open('http://www.t411.io/users/login/', self.getLoginParams())
        except urllib2.URLError as e:
            log.error('Login to T411 failed: %s' % e)
            return False

        if response.getcode() == 200:
            log.debug('Login HTTP T411 status 200; seems successful')
            self.last_login_check = self.opener
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
        if not self.last_login_check and not self.login():
            return
        try:
            request = urllib2.Request(url)
    
            response = self.last_login_check.open(request)
            # unzip if needed
            if response.info().get('Content-Encoding') == 'gzip':
                buf = StringIO(response.read())
                f = gzip.GzipFile(fileobj = buf)
                data = f.read()
                f.close()
            else:
                data = response.read()
            response.close()
            return data
        except:
            return 'try_next'
        
config = [{
    'name': 't411',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 't411',
            'description': 'See <a href="https://www.t411.io/">T411</a>',
            'icon' : 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAA3NCSVQICAjb4U/gAAACdklEQVQokW2RX0hTcRTHz+/+cbvz3m1srbv8M6Ws6SbK1hRTkUoKIui5jIJ8sz9vQQTRQxDRexCkIGgmSC+B1YNWNCIrRQ3Z2PyTf5pb2/S2ud2/2723hyIt/b4cDud7+H4OB2CXrpOW+wYLYPju0R66DTABEAWYB7i6lwHtbEYAKi5crPE36Wa6QGKQyYylk1cePPwX4FqPquSSiZVHAN+Gh/JihpezUpGXinmxkBN5Lvjm5U4/1hzwS5JsJIkzkWnmZDtSZF2WQZZ0SSoIgiSJXq+37VjLNhLL7h/ofUzg0Dceutl1ejHOoa0fScUQW1rouXQWw3ANULXbt8cNJ7pudPrcd/pmLp8PBNpa344HDYTqYc2Ls58G+59sI/0uTgBTKj78OQIdTb6W5gKg+PpKaPprUoLB/mBHY/v/CacARru7ucaG6NCrj5vp2rpDWvmBDa83PzDwdJVOl5Zo8S+JQhoD7E/CGMBEKLyYTNWjLKNl6KkP5OsXbE1leGqdNFoBd3K034jbcJzYfqfPTpUZjOHkmkmS+SpzinXYlxdGM+4I5ezkoyHSUcIjHXHY3wWPqM9SOg2ataFMlvQ6YWs5FIvaKxxgmzEfrWYOazanXuAxAGBwGALoNcWePxtx8cKR4wGuBFZo05TI2gXViE3SaiyVn3bQRgU0DABuVdHn7na6iuSMAOk2X6WnrqLcMVlqTVQ5lHw2VaQURtNN+7YoD7L4cQCQKGo9GJsUEGC6bNPfzc1xpZAjWuH7+3u+xHy+BuFLLkYsx7la0yrCAeqdZg0h1kDQFkpVlSyvrG1krM5mNbtK/9wM0wddjF6UNywElpWVX6HUDxDMdBkmAAAAAElFTkSuQmCC',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
                        {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]

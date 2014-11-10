from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from couchpotato.core.helpers import namer_check
import cookielib
import re
import urllib2
import urllib
from StringIO import StringIO
import gzip
import time
import datetime
log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://addict-to.net/',        
        'detail': 'https://addict-to.net/index.php?page=torrent-details&id=%s',
        'search': 'https://addict-to.net/index.php?page=torrents&',
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
            category=25
        elif 'Documentaire' in moviegenre or 'Documentary' in moviegenre:
            category=48
        elif quality['custom']['3d']==1:
            category=13
        else:    
            
            if moviequality in ['720p']:
                category=15
            elif moviequality in ['1080p']:
                category=14
            elif moviequality in ['dvd-r']:
                category=11
            elif moviequality in ['br-disk']:
                category=49
            elif moviequality in ['bdrip']:
                category=17
            elif moviequality in ['brrip']:
                category=18
            else:
                category=16
            
            
        for MovieTitle in MovieTitles:
            try:
                TitleStringReal = str(MovieTitle.encode("latin-1").replace('-',' '))
            except:
                continue
            try:
                results.append(urllib.urlencode( {'search': TitleStringReal, 'category' : category, 'page' : 'torrents', 'options' : 0, 'active' : 0}))
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
            soup = BeautifulSoup(r,"html5")
            
            resultsTable = soup.find("table", { "class" : "lista" , "width":"100%" })
            if resultsTable:

                rows = resultsTable.findAll("tr")
                x=0
                for row in rows:
                    x=x+1
                    if (x > 1): 
                        #bypass first row because title only
                        link = row.findAll('td')[1].find("a",  href=re.compile("torrent-details"))
                        if link:
                            new={}           
                            title = link.text
                            testname=namer_check.correctName(title,movie)
                            if testname==0:
                                continue
                            downloadURL =  self.urls['test'] + "/" + row.find("a",href=re.compile("\.torrent"))['href']
                            size= row.findAll('td')[8].text
                            leecher=row.findAll('td')[6].text
                            seeder=row.findAll('td')[5].text
                            date=row.findAll('td')[4].text
                            detail=self.urls['test'] + "/" + row.find("a",href=re.compile("torrent-details"))['href']
                            
                            def extra_check(item):
                                return True
                            
                            new['id'] = detail[detail.rfind('=')+1:]
                            new['name'] = title
                            new['url'] = downloadURL
                            new['detail_url'] = detail
                            new['size'] = self.parseSize(size)
                            new['age'] = self.ageToDays(date)
                            new['seeders'] = tryInt(seeder)
                            new['leechers'] = tryInt(leecher)
                            new['extra_check'] = extra_check
                            new['download'] = self.download
            
                            results.append(new)
                 
    def ageToDays(self, age_str):
        try:
            from_dt = datetime.datetime.strptime(age_str[9:11]+'-'+age_str[12:14]+'-'+age_str[15:], "%d-%m-%Y")
        except:
            from_dt = datetime.datetime.strptime(age_str[9:11]+'-'+age_str[12:14]+'-'+age_str[15:], "%m-%d-%Y")
        try:
            to_dt = datetime.datetime.strptime(time.strftime("%x"), "%d/%m/%Y")
        except:
            to_dt = datetime.datetime.strptime(time.strftime("%x"), "%m/%d/%Y")
        timedelta = to_dt - from_dt
        diff_day = timedelta.days
        return tryInt(diff_day)

    def login(self):
       
        self. opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko)'),
            ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
            ('Accept-Language', 'fr-fr,fr;q=0.5'),
            ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
            ('Keep-Alive', '115'),
            ('Connection', 'keep-alive'),
            ('Cache-Control', 'max-age=0'),
        ]
        
        data = urllib.urlencode({'uid': self.conf('username'), 'pwd' :  self.conf('password'), 'submit' : 'Envoyer'})
        
     
        r = self.opener.open('https://addict-to.net/index.php?page=login',data)
        
        for index, cookie in enumerate(self.cj):
            if (cookie.name == "xbtitFM"): login_done = True
                                
        if not login_done:
            log.error('Login to Addict failed')
            return False
        
        if login_done:
            log.debug('Login HTTP Addict status 200; seems successful')
            self.last_login_check = self.opener
            return True 
        
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
    'name': 'addict',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'addict',
            'description': 'See <a href="https://addict-to.net/">Addict</a>',
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

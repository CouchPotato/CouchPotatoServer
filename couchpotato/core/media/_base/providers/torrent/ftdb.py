from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from couchpotato.core.helpers import namer_check
import cookielib
import requests
import re
import urllib2
import urllib
from StringIO import StringIO
import gzip
import time
import datetime
import json

log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'http://www.frenchtorrentdb.com',        
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
        if quality['custom']['3d']==1:
            category='&adv_cat%5Bs%5D%5B7%5D=189'
        else:    
            
            if moviequality in ['720p']:
                category='&adv_cat%5Bm%5D%5B4%5D=136'
            elif moviequality in ['1080p']:
                category='&adv_cat%5Bm%5D%5B5%5D=150'
            elif moviequality in ['dvd-r']:
                category='&adv_cat%5Bm%5D%5B3%5D=82'
            elif moviequality in ['br-disk']:
                category='&adv_cat%5Bm%5D%5B6%5D=187'
            else:
                category='&adv_cat%5Bm%5D%5B1%5D=71'
            
        for MovieTitle in MovieTitles:
            try:
                TitleStringReal = str(MovieTitle.encode("latin-1").replace('-',' '))
            except:
                continue
            try:
                results.append(urllib.urlencode( {'name': TitleStringReal, 'exact':1, 'group': 'films'})+category)
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
            URL = self.urls['test'] + '/?section=TORRENTS&' + searchString.replace('!','')
            
            r = self.opener.open(URL)  
            soup = BeautifulSoup( r, "html5" )
            
            resultsTable = soup.find("div", { "class" : "DataGrid" })
            if resultsTable:
                rows = resultsTable.findAll("ul")

                for row in rows:
                    new={}
                    link = row.find("a", title=True)
                    title = link['title']
                    testname=namer_check.correctName(title,movie)
                    if testname==0:
                        continue
                    size= row.findAll('li')[3].text
                    leecher=row.findAll('li')[5].text
                    seeder=row.findAll('li')[4].text
                    autogetURL = self.urls['test'] +'/'+ (row.find("li", { "class" : "torrents_name"}).find('a')['href'][1:]).replace('#FTD_MENU','&menu=4')
                    r = self.opener.open( autogetURL , 'wb').read()
                    soup = BeautifulSoup( r, "html5" )
                    downloadURL = soup.find("div", { "class" : "autoget"}).find('a')['href']
                    date = soup.find("div", { "class" : "menu_box_stats"}).findAll('div')[4].find('span').text
                    
                    def extra_check(item):
                        return True
                            
                    new['id'] = autogetURL
                    new['name'] = title
                    new['url'] = downloadURL
                    new['detail_url'] = autogetURL
                    new['size'] = self.parseSize(size)
                    new['age'] = self.ageToDays(date)
                    new['seeders'] = tryInt(seeder)
                    new['leechers'] = tryInt(leecher)
                    new['extra_check'] = extra_check
                    new['download'] = self.download
            
                    results.append(new)
                                     
    def ageToDays(self, age_str):
        if 'aujour' in age_str.lower():
            return tryInt('0')
        elif 'hier' in age_str.lower():
            return tryInt('1')
        else:
            try:
                from_dt = datetime.datetime.strptime(age_str[0:2]+'-'+self.littonum(age_str[3:6])+'-'+age_str[7:11], "%d-%m-%Y")
            except:
                from_dt = datetime.datetime.strptime(age_str[0:2]+'-'+self.littonum(age_str[3:6])+'-'+age_str[7:11], "%m-%d-%Y")
            try:
                to_dt = datetime.datetime.strptime(time.strftime("%x"), "%d/%m/%Y")
            except:
                try:
                    to_dt = datetime.datetime.strptime(time.strftime("%x"), "%m/%d/%Y")
                except:
                    try:
                        to_dt = datetime.datetime.strptime(time.strftime("%x"), "%m/%d/%y")
                    except:
                        try:
                            to_dt = datetime.datetime.strptime(time.strftime("%x"), "%d/%m/%y")
                        except:
                            return tryInt('0')
            timedelta = to_dt - from_dt
            diff_day = timedelta.days
            return tryInt(diff_day)
    
    def littonum(self,month):
        
        if month.lower() =='jan':
            return '01'
        elif month.lower() =='feb':
            return '02'
        elif month.lower() =='mar':
            return '03'
        elif month.lower() =='apr':
            return '04'
        elif month.lower() =='may':
            return '05'
        elif month.lower() =='jun':
            return '06'
        elif month.lower() =='jul':
            return '07'
        elif month.lower() =='aug':
            return '08'
        elif month.lower() =='sep':
            return '09'
        elif month.lower() =='oct':
            return '10'
        elif month.lower() =='nov':
            return '11'
        elif month.lower() =='dec':
            return '12'
        else:
            return '01'
    def _getSecureLogin(self, challenges):

        def fromCharCode(*args):
            return ''.join(map(unichr, args))

        def decodeString(p, a, c, k, e, d):
            a = int(a)
            c = int(c)
            def e(c):
                if c < a:
                    f = ''
                else:
                    f = e(c / a)
                return f + fromCharCode(c % a + 161)
            while c:
                c -= 1
                if k[c]:
                    regex = re.compile(e(c))
                    p = re.sub(regex, k[c], p)
            return p

        def decodeChallenge(challenge):
            challenge      = urllib2.unquote(challenge)
            regexGetArgs   = re.compile('\'([^\']+)\',([0-9]+),([0-9]+),\'([^\']+)\'')
            regexIsEncoded = re.compile('decodeURIComponent')
            regexUnquote   = re.compile('\'')
            if (challenge == 'a'):
                return '05f'
            if (re.match(regexIsEncoded, challenge) == None):
                return re.sub(regexUnquote, '', challenge)
            args = re.findall(regexGetArgs, challenge)
            decoded = decodeString(args[0][0], args[0][1], args[0][2], args[0][3].split('|'), 0, {})
            return urllib2.unquote(decoded.decode('utf8'))

        secureLogin = ''
        for challenge in challenges:
            secureLogin += decodeChallenge(challenge)
        return secureLogin

    def login(self):

        challenge = self.opener.open(self.urls['test'] + '/?section=LOGIN&challenge=1')

        rawData = challenge.read()

        data = json.loads(rawData)

        data = urllib.urlencode({
            'username'    : self.conf('username'),
            'password'    : self.conf('password'),
            'secure_login': self._getSecureLogin(data['challenge']),
            'hash'        : data['hash']
        })

        self.opener.open(self.urls['test'] + '/?section=LOGIN&ajax=1', data).read()
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
    'name': 'ftdb',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'ftdb',
            'description': 'See <a href="https://http://www.frenchtorrentdb.com/">FTDB</a>',
            'icon' : 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAACiElEQVQ4EaVTzU8TURCf2tJuS7tQtlRb6UKBIkQwkRRSEzkQgyEc6lkOKgcOph78Y+CgjXjDs2i44FXY9AMTlQRUELZapVlouy3d7kKtb0Zr0MSLTvL2zb75eL838xtTvV6H/xELBptMJojeXLCXyobnyog4YhzXYvmCFi6qVSfaeRdXdrfaU1areV5KykmX06rcvzumjY/1ggkR3Jh+bNf1mr8v1D5bLuvR3qDgFbvbBJYIrE1mCIoCrKxsHuzK+Rzvsi29+6DEbTZz9unijEYI8ObBgXOzlcrx9OAlXyDYKUCzwwrDQx1wVDGg089Dt+gR3mxmhcUnaWeoxwMbm/vzDFzmDEKMMNhquRqduT1KwXiGt0vre6iSeAUHNDE0d26NBtAXY9BACQyjFusKuL2Ry+IPb/Y9ZglwuVscdHaknUChqLF/O4jn3V5dP4mhgRJgwSYm+gV0Oi3XrvYB30yvhGa7BS70eGFHPoTJyQHhMK+F0ZesRVVznvXw5Ixv7/C10moEo6OZXbWvlFAF9FVZDOqEABUMRIkMd8GnLwVWg9/RkJF9sA4oDfYQAuzzjqzwvnaRUFxn/X2ZlmGLXAE7AL52B4xHgqAUqrC1nSNuoJkQtLkdqReszz/9aRvq90NOKdOS1nch8TpL555WDp49f3uAMXhACRjD5j4ykuCtf5PP7Fm1b0DIsl/VHGezzP1KwOiZQobFF9YyjSRYQETRENSlVzI8iK9mWlzckpSSCQHVALmN9Az1euDho9Xo8vKGd2rqooA8yBcrwHgCqYR0kMkWci08t/R+W4ljDCanWTg9TJGwGNaNk3vYZ7VUdeKsYJGFNkfSzjXNrSX20s4/h6kB81/271ghG17l+rPTAAAAAElFTkSuQmCC',
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

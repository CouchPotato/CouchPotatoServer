from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
import cookielib
import re
import traceback
import urllib
import urllib2
import unicodedata
from couchpotato.core.helpers import namer_check

log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'http://www.cpasbien.pw/',
        'search': 'http://www.cpasbien.pw/recherche/',
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
                raise Base.NotLoggedInHTTPError(req.get_full_url(), code, msg, headers, fp)

    def _search(self, movie, quality, results):

                # Cookie login
        if not self.last_login_check and not self.login():
            return


        TitleStringReal = (getTitle(movie['info']) + ' ' + simplifyString(quality['identifier'] )).replace('-',' ').replace(' ',' ').replace(' ',' ').replace(' ',' ').encode("utf8")
        
        URL = (self.urls['search']).encode('UTF8')
        URL=unicodedata.normalize('NFD',unicode(URL,"utf8","replace"))
        URL=URL.encode('ascii','ignore')
        URL = urllib2.quote(URL.encode('utf8'), ":/?=")
        
        values = {
          'champ_recherche' : TitleStringReal
        }

        data_tmp = urllib.urlencode(values)
        req = urllib2.Request(URL, data_tmp, headers={'User-Agent' : "Mozilla/5.0"} )
        
        data = urllib2.urlopen(req )
       
        id = 1000

        if data:
                       
            try:
                html = BeautifulSoup(data)
                lin=0
                erlin=0
                resultdiv=[]
                while erlin==0:
                    try:
                        classlin='ligne'+str(lin)
                        resultlin=html.findAll(attrs = {'class' : [classlin]})
                        if resultlin:
                            for ele in resultlin:
                                resultdiv.append(ele)
                            lin+=1
                        else:
                            erlin=1
                    except:
                        erlin=1
                for result in resultdiv:

                    try:
                        
                        new = {}
                        name = result.findAll(attrs = {'class' : ["titre"]})[0].text
                        testname=namer_check.correctName(name,movie)
                        if testname==0:
                            continue
                        detail_url = result.find("a")['href']
                        tmp = detail_url.split('/')[-1].replace('.html','.torrent')
                        url_download = ('http://www.cpasbien.pw/telechargement/%s' % tmp)
                        size = result.findAll(attrs = {'class' : ["poid"]})[0].text
                        seeder = result.findAll(attrs = {'class' : ["seed_ok"]})[0].text
                        leecher = result.findAll(attrs = {'class' : ["down"]})[0].text
                        age = '1'

                        verify = getTitle(movie['info']).split(' ')
                        
                        add = 1
                        
                        for verify_unit in verify:
                            if (name.lower().find(verify_unit.lower()) == -1) :
                                add = 0

                        def extra_check(item):
                            return True

                        if add == 1:

                            new['id'] = id
                            new['name'] = name.strip()
                            new['url'] = url_download
                            new['detail_url'] = detail_url
                           
                            new['size'] = self.parseSize(size)
                            new['age'] = self.ageToDays(age)
                            new['seeders'] = tryInt(seeder)
                            new['leechers'] = tryInt(leecher)
                            new['extra_check'] = extra_check
                            new['download'] = self.loginDownload             
    
                            #new['score'] = fireEvent('score.calculate', new, movie, single = True)
    
                            #log.error('score')
                            #log.error(new['score'])
    
                            results.append(new)
    
                            id = id+1
                        
                    except:
                        log.error('Failed parsing cPASbien: %s', traceback.format_exc())

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
        opener = urllib2.build_opener(cookieprocessor, Base.PTPHTTPRedirectHandler())
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
            response = opener.open('http://www.cpasbien.pw', tryUrlencode({'url': '/'}))
        except urllib2.URLError as e:
            log.error('Login to cPASbien failed: %s' % e)
            return False

        if response.getcode() == 200:
            log.debug('Login HTTP cPASbien status 200; seems successful')
            self.last_login_check = opener
            return True
        else:
            log.error('Login to cPASbien failed: returned code %d' % response.getcode())
            return False
        
        
    def loginDownload(self, url = '', nzb_id = ''):
        values = {
          'url' : '/'
        }
        data_tmp = urllib.urlencode(values)
        req = urllib2.Request(url, data_tmp, headers={'User-Agent' : "Mozilla/5.0"} )
        
        try:
            if not self.last_login_check and not self.login():
                log.error('Failed downloading from %s', self.getName())
            return urllib2.urlopen(req).read()
        except:
            log.error('Failed downloading from %s: %s', (self.getName(), traceback.format_exc()))
            
    def download(self, url = '', nzb_id = ''):
        
        if not self.last_login_check and not self.login():
            return
        
        values = {
          'url' : '/'
        }
        data_tmp = urllib.urlencode(values)
        req = urllib2.Request(url, data_tmp, headers={'User-Agent' : "Mozilla/5.0"} )
        
        try:
            return urllib2.urlopen(req).read()
        except:
            log.error('Failed downloading from %s: %s', (self.getName(), traceback.format_exc()))
config = [{
    'name': 'cpasbien',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'cpasbien',
            'description': 'See <a href="http://www.cpasbien.pw/">cPASbien</a>',
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAgZJREFUOI2lkj9oE2EYxn93l/Quf440gXg4lBoEMd2MDuLSkk0R6hCnuqjUoR0c7FDo4Ca0CDo7uRRBqEMDXSLUUqRDiZM1NMEI1VKTlDZpUppccvc5nJp/KooPfMPH+z3P+zzv+8F/Quq8XIVEEOY0kASIzpoLlBKUV+CuCblfCjyF/P3V1Qi6jrCs7k4eD/X1dS5NTy9tQaJD2MFDkA23W8UwQFGQRJcB0DS0cBg/DPY4a0OVZcHeHihKf1ifD6pVfGD/VmBAUeDwEGQZLAskCVQV6nVYW+M4lSLQo9stoKpQLoNtO2QhYHsbkkmOczm+AP5eBy/BfwRDn8GHJLkpFp3utRpkMpDLwckJvlCIM9Uqg6YZeAAj58E1CVlXCaaigcCjsWhU8Xq9UCo5lisVx4FhODFkGbdpMtlqXa4IsVUHYkLcVlbg3ddGo3AzErl2emLCGaCmwcAAuL4ntCxoNpFsG8O2odlkXojF17CgAK2PsJna2Xk/ViyOh0dHXWhaewaW1T6mSb5a5V6rtbAMU4D5c18FyCzu7i5fyWZvDMfjOh4PNBpd5A/5vLheq93ZhMc/eF0Lr0NhaX8/eS6djo/EYqfQdUekUuHNxsZR4uDg1id40f9J+qE/CwTeitlZIWZmxKtQqOSFi39D7IQy5/c/fxIMpoGhfyUDMAwXzsL4n958A9jfxsJ8X4WQAAAAAElFTkSuQmCC',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
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

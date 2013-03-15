from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.helpers.variable import getTitle, mergeDicts
from couchpotato.core.providers.torrent.base import TorrentProvider
from dateutil.parser import parse
import cookielib
import htmlentitydefs
import json
import re
import time
import traceback
import urllib2
import unicodedata

log = CPLog(__name__)


class t411(TorrentProvider):

    urls = {
        'test': 'http://www.t411.me/',
        'detail': 'http://www.t411.me/torrents/?id=%s',
        'search': 'http://www.t411.me/torrents/search/?search=%s %s',
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

    def _search(self, movie, quality, results):

        # Cookie login
        if not self.login_opener and not self.login():
            return

        #dataTitle = self.getHTMLData("http://www.imdb.fr/title/%s/" % (movie['library']['identifier']))

        TitleStringReal = ""

        #if dataTitle:
        #    try:
        #        htmlTitle = BeautifulSoup(dataTitle)
        #        TitleString = htmlTitle.find('div', attrs = {'id':'tn15title'}).find('h1')
        #
        #        TitleStringReal = TitleString.text.replace(TitleString.find('span').text,'')
        #        TitleStringReal = TitleStringReal.strip()
        #
        #    except:
        #        log.error('Failed parsing T411: %s', traceback.format_exc())

        TitleStringReal = getTitle(movie['library'])


        URL = (self.urls['search'] % (simplifyString(TitleStringReal), simplifyString(quality['identifier'] ))).replace('-',' ').replace('  ',' ').replace('  ',' ').replace('  ',' ').encode("utf8")
        URL=unicodedata.normalize('NFD',unicode(URL,"utf8","replace"))
        URL=URL.encode('ascii','ignore')

        URL = urllib2.quote(URL.encode('utf8'), ":/?=")

        data = self.getHTMLData(URL , opener = self.login_opener)

        if data:

            cat_ids = self.getCatId(quality['identifier'])
            table_order = ['name', 'size', None, 'age', 'seeds', 'leechers']

            log.debug('Il y a des donnee')

            try:
                html = BeautifulSoup(data)

                resultdiv = html.find('table', attrs = {'class':'results'}).find('tbody')

                for result in resultdiv.find_all('tr', recursive = False):

                    try:

                        new = {}

                        id = result.find_all('td')[2].find_all('a')[0]['href'][1:].replace('torrents/nfo/?id=','')
                        name = result.find_all('td')[1].find_all('a')[0]['title']
                        url = ('http://www.t411.me/torrents/download/?id=%s' % id)
                        detail_url = ('http://www.t411.me/torrents/?id=%s' % id)

                        size = result.find_all('td')[5].text
                        age = result.find_all('td')[4].text
                        seeder = result.find_all('td')[7].text
                        leecher = result.find_all('td')[8].text
                        #score = 10
                        #score = score + (self.parseSize(size) // 1024) * 2 + tryInt(seeder)

                        def extra_check(item):
                            return True

                        log.debug(name)

                        new['id'] = id
                        new['name'] = name + ' french'
                        new['url'] = url
                        new['detail_url'] = detail_url
                        #new['score'] = score
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

        log.debug('Try login T411')

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

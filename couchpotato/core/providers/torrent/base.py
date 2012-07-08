from couchpotato.core.helpers.variable import getImdb, md5
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import YarrProvider
import cookielib
import traceback
import urllib2

log = CPLog(__name__)


class TorrentProvider(YarrProvider):

    type = 'torrent'
    login_opener = None

    def imdbMatch(self, url, imdbId):
        if getImdb(url) == imdbId:
            return True

        if url[:4] == 'http':
            try:
                cache_key = md5(url)
                data = self.getCache(cache_key, url)
            except IOError:
                log.error('Failed to open %s.', url)
                return False

            return getImdb(data) == imdbId

        return False

    def login(self):

        try:
            cookiejar = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
            urllib2.install_opener(opener)
            f = opener.open(self.urls['login'], self.getLoginParams())
            f.read()
            f.close()
            self.login_opener = opener
            return True
        except:
            log.error('Failed to login %s: %s', (self.getName(), traceback.format_exc()))

        return False

    def loginDownload(self, url = '', nzb_id = ''):
        try:
            if not self.login_opener and not self.login():
                log.error('Failed downloading from %s', self.getName())
            return self.urlopen(url, opener = self.login_opener)
        except:
            log.error('Failed downloading from %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return ''

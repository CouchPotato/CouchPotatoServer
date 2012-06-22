from couchpotato.core.providers.base import YarrProvider
from couchpotato.core.logger import CPLog
import urllib2
import cookielib

log = CPLog(__name__)


class TorrentProvider(YarrProvider):
    type = 'torrent'

    def login(self, params):
        
        try:
            cookiejar = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
            urllib2.install_opener(opener)
            f = opener.open(self.urls['login'], params)
            data = f.read()
            f.close()
        
        except:    
            log.error('Failed to login.')
        
        return opener  
        
    def download(self, url = '', nzb_id = ''):
        loginParams = self.getLoginParams()
        self.login(params = loginParams)
        torrent = self.urlopen(url)
        return torrent

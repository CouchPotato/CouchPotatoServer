from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
import traceback
import base64

log = CPLog(__name__)

class Sabnzbd(Downloader):

    type = ['nzb']

    def download(self, data = {}, movie = {}, manual = False, filedata = None):

        if self.isDisabled(manual) or not self.isCorrectType(data.get('type')):
            return

        log.info('Sending "%s" to SABnzbd.', data.get('name'))

        params = {
            'apikey': self.conf('api_key'),
            'cat': self.conf('category'),
            'mode': 'addurl',
            'nzbname': self.createNzbName(data, movie),
        }
        
        headers = {}
        if self.conf('password'):
            headers = {
               'Authorization': "Basic %s" % base64.encodestring('%s:%s' % (self.conf('username'), self.conf('password')))[:-1]
            }

        if filedata:
            if len(filedata) < 50:
                log.error('No proper nzb available!')
                return False

            # If it's a .rar, it adds the .rar extension, otherwise it stays .nzb
            nzb_filename = self.createFileName(data, filedata, movie)
            params['mode'] = 'addfile'
        else:
            params['name'] = data.get('url')

        url = cleanHost(self.conf('host')) + "api?" + tryUrlencode(params)

        try:
            if params.get('mode') is 'addfile':
                data = self.urlopen(url, timeout = 60, params = {"nzbfile": (nzb_filename, filedata)}, headers = headers, multipart = True, show_error = False)
            else:
                data = self.urlopen(url, timeout = 60, headers = headers, show_error = False)
        except:
            log.error(traceback.format_exc())
            return False

        result = data.strip()
        if not result:
            log.error("SABnzbd didn't return anything.")
            return False

        log.debug("Result text from SAB: " + result[:40])
        if result == "ok":
            log.info("NZB sent to SAB successfully.")
            return True
        elif result == "Missing authentication":
            log.error("Incorrect username/password.")
            return False
        else:
            log.error("Unknown error: " + result[:40])
            return False

from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
import traceback
import json

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
                data = self.urlopen(url, timeout = 60, params = {"nzbfile": (nzb_filename, filedata)}, multipart = True, show_error = False)
            else:
                data = self.urlopen(url, timeout = 60, show_error = False)
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

    def getdownloadfailed(self, data = {}, movie = {}):
        if self.isDisabled(manual = True) or not self.isCorrectType(data.get('type')):
            return

        if not self.conf('download failed', default = True):
            return False

        log.info('Checking download status of "%s" at SABnzbd.', data.get('name'))

        params = {
            'apikey': self.conf('api_key'),
            'mode': 'history',
            'output': 'json'
        }
        url = cleanHost(self.conf('host')) + "api?" + tryUrlencode(params)
        log.debug('Opening: %s', url)

        try:
            history = json.load(self.urlopen(url))
        except:
            log.error(traceback.format_exc())
            return False 

        nzbname = self.createNzbName(data, movie)

        # Go through history items
        for slot in history['history']['slots']:
            log.debug('Found %s in SabNZBd history, which has %s', (slot['name'], slot['status']))
            if slot['name'] == nzbname and slot['status'] == 'Failed':

                # Delete failed download
                if self.conf('delete failed',  default = True):
                    log.info('%s failed downloading, deleting...', slot['name'])
                    params = {
                        'apikey': self.conf('api_key'),
                        'mode': 'history',
                        'name': 'delete',
                        'del_files': '1',
                        'value': slot['nzo_id']
                    }
                    url = cleanHost(self.conf('host')) + "api?" + tryUrlencode(params)
                    try:
                        data = self.urlopen(url, timeout = 60, show_error = False)
                    except:
                        log.error(traceback.format_exc())

                # Return download failed
                return True

        return False

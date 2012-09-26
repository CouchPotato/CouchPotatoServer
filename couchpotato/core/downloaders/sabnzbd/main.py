from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
import json
import traceback

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
                sab = self.urlopen(url, timeout = 60, params = {"nzbfile": (nzb_filename, filedata)}, multipart = True, show_error = False)
            else:
                sab = self.urlopen(url, timeout = 60, show_error = False)
        except:
            log.error('Failed sending release: %s', traceback.format_exc())
            return False

        result = sab.strip()
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

    def getDownloadStatus(self, data = {}, movie = {}):
        if self.isDisabled(manual = True) or not self.isCorrectType(data.get('type')):
            return

        log.info('Checking SABnzbd download status.')

        # Go through Queue
        params = {
            'apikey': self.conf('api_key'),
            'mode': 'queue',
            'output': 'json'
        }
        url = cleanHost(self.conf('host')) + "api?" + tryUrlencode(params)

        try:
            sab = self.urlopen(url, timeout = 60, show_error = False)
        except:
            log.error('Failed checking status: %s', traceback.format_exc())
            return False

        try:
            queue = json.loads(sab)
        except:
            log.debug("Result text from SAB: " + sab[:40])
            log.error('Failed parsing json status: %s', traceback.format_exc())
            return False

        # Go through history items
        params = {
            'apikey': self.conf('api_key'),
            'mode': 'history',
            'limit': 15,
            'output': 'json'
        }
        url = cleanHost(self.conf('host')) + "api?" + tryUrlencode(params)

        try:
            sab = self.urlopen(url, timeout = 60, show_error = False)
        except:
            log.error('Failed getting history: %s', traceback.format_exc())
            return False

        try:
            history = json.loads(sab)
        except:
            log.debug("Result text from SAB: " + sab[:40])
            log.error('Failed parsing history json: %s', traceback.format_exc())
            return False

        return queue, history

    def remove(self, name = {}, nzo_id = {}):
        # Delete failed download
        if self.conf('delete_failed', default = True):

            log.info('%s failed downloading, deleting...', name)
            params = {
                'apikey': self.conf('api_key'),
                'mode': 'history',
                'name': 'delete',
                'del_files': '1',
                'value': nzo_id
            }
            url = cleanHost(self.conf('host')) + "api?" + tryUrlencode(params)

            try:
                sab = self.urlopen(url, timeout = 60, show_error = False)
            except:
                log.error('Failed deleting: %s', traceback.format_exc())
                return False

            result = sab.strip()
            if not result:
                log.error("SABnzbd didn't return anything.")

            log.debug("Result text from SAB: " + result[:40])
            if result == "ok":
                log.info('SabNZBd deleted failed release %s successfully.', name)
            elif result == "Missing authentication":
                log.error("Incorrect username/password or API?.")
            else:
                log.error("Unknown error: " + result[:40])
            return

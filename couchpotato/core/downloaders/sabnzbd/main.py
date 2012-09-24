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

        nzbname = self.createNzbName(data, movie)
        log.info('Checking download status of "%s" at SABnzbd.', nzbname)

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
            history = json.loads(sab)
        except:
            log.debug("Result text from SAB: " + sab[:40])
            log.error('Failed parsing json status: %s', traceback.format_exc())
            return False

        try:
            for slot in history['queue']['slots']:
                log.debug('Found %s in SabNZBd queue, which is %s, with %s left', (slot['filename'], slot['status'], slot['timeleft']))
                if slot['filename'] == nzbname:
                    return slot['status'].lower()
        except:
            log.debug('No items in queue: %s', (traceback.format_exc()))

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
            return

        try:
            history = json.loads(sab)
        except:
            log.debug("Result text from SAB: " + sab[:40])
            log.error('Failed parsing history json: %s', traceback.format_exc())
            return

        try:
            for slot in history['history']['slots']:
                log.debug('Found %s in SabNZBd history, which has %s', (slot['name'], slot['status']))
                if slot['name'] == nzbname:
                    # Note: if post process even if failed is on in SabNZBd, it will complete with a fail message
                    if slot['status'] == 'Failed' or (slot['status'] == 'Completed' and slot['fail_message'].strip()):

                        # Delete failed download
                        if self.conf('delete_failed', default = True):

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
                                sab = self.urlopen(url, timeout = 60, show_error = False)
                            except:
                                log.error('Failed deleting: %s', traceback.format_exc())
                                return False

                            result = sab.strip()
                            if not result:
                                log.error("SABnzbd didn't return anything.")

                            log.debug("Result text from SAB: " + result[:40])
                            if result == "ok":
                                log.info('SabNZBd deleted failed release %s successfully.', slot['name'])
                            elif result == "Missing authentication":
                                log.error("Incorrect username/password or API?.")
                            else:
                                log.error("Unknown error: " + result[:40])

                        return 'failed'
                    else:
                        return slot['status'].lower()
        except:
            log.debug('No items in history: %s', (traceback.format_exc()))

        return 'not_found'

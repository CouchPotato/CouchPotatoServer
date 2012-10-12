from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import cleanHost, mergeDicts
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

    def getAllDownloadStatus(self):
        if self.isDisabled(manual = False):
            return False

        log.debug('Checking SABnzbd download status.')

        # Go through Queue
        try:
            queue = self.call({
                'mode': 'queue',
            })
        except:
            log.error('Failed getting queue: %s', traceback.format_exc())
            return False

        # Go through history items
        try:
            history = self.call({
                'mode': 'history',
                'limit': 15,
            })
        except:
            log.error('Failed getting history json: %s', traceback.format_exc())
            return False

        statuses = []

        # Get busy releases
        for item in queue.get('slots', []):
            statuses.append({
                'id': item['nzo_id'],
                'name': item['filename'],
                'status': 'busy',
                'original_status': item['status'],
                'timeleft': item['timeleft'] if not queue['paused'] else -1,
            })

        # Get old releases
        for item in history.get('slots', []):

            status = 'busy'
            if item['status'] == 'Failed' or (item['status'] == 'Completed' and item['fail_message'].strip()):
                status = 'failed'
            elif item['status'] == 'Completed':
                status = 'completed'

            statuses.append({
                'id': item['nzo_id'],
                'name': item['name'],
                'status': status,
                'original_status': item['status'],
                'timeleft': 0,
            })

        return statuses

    def removeFailed(self, item):

        if not self.conf('delete_failed', default = True):
            return False

        log.info('%s failed downloading, deleting...', item['name'])

        try:
            self.call({
                'mode': 'history',
                'name': 'delete',
                'del_files': '1',
                'value': item['id']
            }, use_json = False)
        except:
            log.error('Failed deleting: %s', traceback.format_exc())
            return False

        return True

    def call(self, params, use_json = True):

        url = cleanHost(self.conf('host')) + "api?" + tryUrlencode(mergeDicts(params, {
           'apikey': self.conf('api_key'),
           'output': 'json'
        }))

        data = self.urlopen(url, timeout = 60, show_error = False)
        if use_json:
            return json.loads(data)[params['mode']]
        else:
            return data


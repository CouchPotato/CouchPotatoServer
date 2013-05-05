from couchpotato.core.downloaders.base import Downloader, StatusList
from couchpotato.core.helpers.encoding import tryUrlencode, ss
from couchpotato.core.helpers.variable import cleanHost, mergeDicts
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
from datetime import timedelta
from urllib2 import URLError
import json
import traceback

log = CPLog(__name__)

class Sabnzbd(Downloader):

    type = ['nzb']

    def download(self, data = {}, movie = {}, filedata = None):

        log.info('Sending "%s" to SABnzbd.', data.get('name'))

        req_params = {
            'cat': self.conf('category'),
            'mode': 'addurl',
            'nzbname': self.createNzbName(data, movie),
        }

        if filedata:
            if len(filedata) < 50:
                log.error('No proper nzb available: %s', (filedata))
                return False

            # If it's a .rar, it adds the .rar extension, otherwise it stays .nzb
            nzb_filename = self.createFileName(data, filedata, movie)
            req_params['mode'] = 'addfile'
        else:
            req_params['name'] = data.get('url')

        try:
            if req_params.get('mode') is 'addfile':
                sab_data = self.call(req_params, params = {'nzbfile': (ss(nzb_filename), filedata)}, multipart = True)
            else:
                sab_data = self.call(req_params)
        except URLError:
            log.error('Failed sending release, probably wrong HOST: %s', traceback.format_exc(0))
            return False
        except:
            log.error('Failed sending release, use API key, NOT the NZB key: %s', traceback.format_exc(0))
            return False

        log.debug('Result from SAB: %s', sab_data)
        if sab_data.get('status') and not sab_data.get('error'):
            log.info('NZB sent to SAB successfully.')
            if filedata:
                return self.downloadReturnId(sab_data.get('nzo_ids')[0])
            else:
                return True
        else:
            log.error('Error getting data from SABNZBd: %s', sab_data)
            return False

    def getAllDownloadStatus(self):

        log.debug('Checking SABnzbd download status.')

        # Go through Queue
        try:
            queue = self.call({
                'mode': 'queue',
            })
        except:
            log.error('Failed getting queue: %s', traceback.format_exc(1))
            return False

        # Go through history items
        try:
            history = self.call({
                'mode': 'history',
                'limit': 15,
            })
        except:
            log.error('Failed getting history json: %s', traceback.format_exc(1))
            return False

        statuses = StatusList(self)

        # Get busy releases
        for item in queue.get('slots', []):
            statuses.append({
                'id': item['nzo_id'],
                'name': item['filename'],
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
                'timeleft': str(timedelta(seconds = 0)),
                'folder': item['storage'],
            })

        return statuses

    def removeFailed(self, item):

        log.info('%s failed downloading, deleting...', item['name'])

        try:
            self.call({
                'mode': 'history',
                'name': 'delete',
                'del_files': '1',
                'value': item['id']
            }, use_json = False)
        except:
            log.error('Failed deleting: %s', traceback.format_exc(0))
            return False

        return True

    def call(self, request_params, use_json = True, **kwargs):

        url = cleanHost(self.conf('host')) + 'api?' + tryUrlencode(mergeDicts(request_params, {
           'apikey': self.conf('api_key'),
           'output': 'json'
        }))

        data = self.urlopen(url, timeout = 60, show_error = False, headers = {'User-Agent': Env.getIdentifier()}, **kwargs)
        if use_json:
            d = json.loads(data)
            if d.get('error'):
                log.error('Error getting data from SABNZBd: %s', d.get('error'))
                return {}

            return d.get(request_params['mode']) or d
        else:
            return data


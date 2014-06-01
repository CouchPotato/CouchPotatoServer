from datetime import timedelta
from urllib2 import URLError
import json
import os
import traceback

from couchpotato.core._base.downloader.main import DownloaderBase, ReleaseDownloadList
from couchpotato.core.helpers.encoding import tryUrlencode, ss, sp
from couchpotato.core.helpers.variable import cleanHost, mergeDicts
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env


log = CPLog(__name__)

autoload = 'Sabnzbd'


class Sabnzbd(DownloaderBase):

    protocol = ['nzb']

    def download(self, data = None, media = None, filedata = None):
        if not media: media = {}
        if not data: data = {}

        log.info('Sending "%s" to SABnzbd.', data.get('name'))

        req_params = {
            'cat': self.conf('category'),
            'mode': 'addurl',
            'nzbname': self.createNzbName(data, media),
            'priority': self.conf('priority'),
        }

        nzb_filename = None
        if filedata:
            if len(filedata) < 50:
                log.error('No proper nzb available: %s', filedata)
                return False

            # If it's a .rar, it adds the .rar extension, otherwise it stays .nzb
            nzb_filename = self.createFileName(data, filedata, media)
            req_params['mode'] = 'addfile'
        else:
            req_params['name'] = data.get('url')

        try:
            if nzb_filename and req_params.get('mode') is 'addfile':
                sab_data = self.call(req_params, files = {'nzbfile': (ss(nzb_filename), filedata)})
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

    def test(self):
        try:
            sab_data = self.call({
                'mode': 'version',
            })
            v = sab_data.split('.')
            if int(v[0]) == 0 and int(v[1]) < 7:
                return False, 'Your Sabnzbd client is too old, please update to newest version.'

            # the version check will work even with wrong api key, so we need the next check as well
            sab_data = self.call({
                'mode': 'qstatus',
            })
            if not sab_data:
                return False
        except:
            return False

        return True

    def getAllDownloadStatus(self, ids):

        log.debug('Checking SABnzbd download status.')

        # Go through Queue
        try:
            queue = self.call({
                'mode': 'queue',
            })
        except:
            log.error('Failed getting queue: %s', traceback.format_exc(1))
            return []

        # Go through history items
        try:
            history = self.call({
                'mode': 'history',
                'limit': 15,
            })
        except:
            log.error('Failed getting history json: %s', traceback.format_exc(1))
            return []

        release_downloads = ReleaseDownloadList(self)

        # Get busy releases
        for nzb in queue.get('slots', []):
            if nzb['nzo_id'] in ids:
                status = 'busy'
                if 'ENCRYPTED / ' in nzb['filename']:
                    status = 'failed'

                release_downloads.append({
                    'id': nzb['nzo_id'],
                    'name': nzb['filename'],
                    'status': status,
                    'original_status': nzb['status'],
                    'timeleft': nzb['timeleft'] if not queue['paused'] else -1,
                })

        # Get old releases
        for nzb in history.get('slots', []):
            if nzb['nzo_id'] in ids:
                status = 'busy'
                if nzb['status'] == 'Failed' or (nzb['status'] == 'Completed' and nzb['fail_message'].strip()):
                    status = 'failed'
                elif nzb['status'] == 'Completed':
                    status = 'completed'

                release_downloads.append({
                    'id': nzb['nzo_id'],
                    'name': nzb['name'],
                    'status': status,
                    'original_status': nzb['status'],
                    'timeleft': str(timedelta(seconds = 0)),
                    'folder': sp(os.path.dirname(nzb['storage']) if os.path.isfile(nzb['storage']) else nzb['storage']),
                })

        return release_downloads

    def removeFailed(self, release_download):

        log.info('%s failed downloading, deleting...', release_download['name'])

        try:
            self.call({
                'mode': 'queue',
                'name': 'delete',
                'del_files': '1',
                'value': release_download['id']
            }, use_json = False)
            self.call({
                'mode': 'history',
                'name': 'delete',
                'del_files': '1',
                'value': release_download['id']
            }, use_json = False)
        except:
            log.error('Failed deleting: %s', traceback.format_exc(0))
            return False

        return True

    def processComplete(self, release_download, delete_files = False):
        log.debug('Requesting SabNZBd to remove the NZB %s.', release_download['name'])

        try:
            self.call({
                'mode': 'history',
                'name': 'delete',
                'del_files': '0',
                'value': release_download['id']
            }, use_json = False)
        except:
            log.error('Failed removing: %s', traceback.format_exc(0))
            return False

        return True

    def call(self, request_params, use_json = True, **kwargs):

        url = cleanHost(self.conf('host'), ssl = self.conf('ssl')) + 'api?' + tryUrlencode(mergeDicts(request_params, {
            'apikey': self.conf('api_key'),
            'output': 'json'
        }))

        data = self.urlopen(url, timeout = 60, show_error = False, verify_ssl = False, headers = {'User-Agent': Env.getIdentifier()}, **kwargs)
        if use_json:
            d = json.loads(data)
            if d.get('error'):
                log.error('Error getting data from SABNZBd: %s', d.get('error'))
                return {}

            return d.get(request_params['mode']) or d
        else:
            return data


config = [{
    'name': 'sabnzbd',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'sabnzbd',
            'label': 'Sabnzbd',
            'description': 'Use <a href="http://sabnzbd.org/" target="_blank">SABnzbd</a> (0.7+) to download NZBs.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'nzb',
                },
                {
                    'name': 'host',
                    'default': 'localhost:8080',
                },
                {
                    'name': 'ssl',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Use HyperText Transfer Protocol Secure, or <strong>https</strong>',
                },
                {
                    'name': 'api_key',
                    'label': 'Api Key',
                    'description': 'Used for all calls to Sabnzbd.',
                },
                {
                    'name': 'category',
                    'label': 'Category',
                    'description': 'The category CP places the nzb in. Like <strong>movies</strong> or <strong>couchpotato</strong>',
                },
                {
                    'name': 'priority',
                    'label': 'Priority',
                    'type': 'dropdown',
                    'default': '0',
                    'advanced': True,
                    'values': [('Paused', -2), ('Low', -1), ('Normal', 0), ('High', 1), ('Forced', 2)],
                    'description': 'Add to the queue with this priority.',
                },
                {
                    'name': 'manual',
                    'default': False,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Disable this downloader for automated searches, but use it when I manually send a release.',
                },
                {
                    'name': 'remove_complete',
                    'advanced': True,
                    'label': 'Remove NZB',
                    'default': False,
                    'type': 'bool',
                    'description': 'Remove the NZB from history after it completed.',
                },
                {
                    'name': 'delete_failed',
                    'default': True,
                    'advanced': True,
                    'type': 'bool',
                    'description': 'Delete a release after the download has failed.',
                },
            ],
        }
    ],
}]

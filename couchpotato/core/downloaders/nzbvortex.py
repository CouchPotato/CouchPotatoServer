from base64 import b64encode
import os
from uuid import uuid4
import hashlib
import traceback

from requests import HTTPError

from couchpotato.core._base.downloader.main import DownloaderBase, ReleaseDownloadList
from couchpotato.core.helpers.encoding import tryUrlencode, sp
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog


log = CPLog(__name__)

autoload = 'NZBVortex'


class NZBVortex(DownloaderBase):

    protocol = ['nzb']
    api_level = None
    session_id = None

    def download(self, data = None, media = None, filedata = None):
        """ Send a torrent/nzb file to the downloader

        :param data: dict returned from provider
            Contains the release information
        :param media: media dict with information
            Used for creating the filename when possible
        :param filedata: downloaded torrent/nzb filedata
            The file gets downloaded in the searcher and send to this function
            This is done to have failed checking before using the downloader, so the downloader
            doesn't need to worry about that
        :return: boolean
            One faile returns false, but the downloaded should log his own errors
        """

        if not media: media = {}
        if not data: data = {}

        # Send the nzb
        try:
            nzb_filename = self.createFileName(data, filedata, media, unique_tag = True)
            response = self.call('nzb/add', files = {'file': (nzb_filename, filedata, 'application/octet-stream')}, parameters = {
                'name': nzb_filename,
                'groupname': self.conf('group')
            })

            if response and response.get('result', '').lower() == 'ok':
                return self.downloadReturnId(nzb_filename)

            log.error('Something went wrong sending the NZB file. Response: %s', response)
            return False
        except:
            log.error('Something went wrong sending the NZB file: %s', traceback.format_exc())
            return False

    def test(self):
        """ Check if connection works
        :return: bool
        """

        try:
            login_result = self.login()
        except:
            return False

        return login_result

    def getAllDownloadStatus(self, ids):
        """ Get status of all active downloads

        :param ids: list of (mixed) downloader ids
            Used to match the releases for this downloader as there could be
            other downloaders active that it should ignore
        :return: list of releases
        """

        raw_statuses = self.call('nzb')

        release_downloads = ReleaseDownloadList(self)
        for nzb in raw_statuses.get('nzbs', []):
            nzb_id = os.path.basename(nzb['nzbFileName'])
            if nzb_id in ids:

                # Check status
                status = 'busy'
                if nzb['state'] == 20:
                    status = 'completed'
                elif nzb['state'] in [21, 22, 24]:
                    status = 'failed'

                release_downloads.append({
                    'temp_id': nzb['id'],
                    'id': nzb_id,
                    'name': nzb['uiTitle'],
                    'status': status,
                    'original_status': nzb['state'],
                    'timeleft': -1,
                    'folder': sp(nzb['destinationPath']),
                })

        return release_downloads

    def removeFailed(self, release_download):

        log.info('%s failed downloading, deleting...', release_download['name'])

        try:
            self.call('nzb/%s/cancel' % release_download['temp_id'])
        except:
            log.error('Failed deleting: %s', traceback.format_exc(0))
            return False

        return True

    def login(self):

        nonce = self.call('auth/nonce', auth = False).get('authNonce')
        cnonce = uuid4().hex
        hashed = b64encode(hashlib.sha256('%s:%s:%s' % (nonce, cnonce, self.conf('api_key'))).digest())

        params = {
            'nonce': nonce,
            'cnonce': cnonce,
            'hash': hashed
        }

        login_data = self.call('auth/login', parameters = params, auth = False)

        # Save for later
        if login_data.get('loginResult') == 'successful':
            self.session_id = login_data.get('sessionID')
            return True

        log.error('Login failed, please check you api-key')
        return False

    def call(self, call, parameters = None, is_repeat = False, auth = True, *args, **kwargs):

        # Login first
        if not parameters: parameters = {}
        if not self.session_id and auth:
            self.login()

        # Always add session id to request
        if self.session_id:
            parameters['sessionid'] = self.session_id

        params = tryUrlencode(parameters)

        url = cleanHost(self.conf('host')) + 'api/' + call

        try:
            data = self.getJsonData('%s%s' % (url, '?' + params if params else ''), *args, cache_timeout = 0, show_error = False, **kwargs)

            if data:
                return data
        except HTTPError as e:
            sc = e.response.status_code
            if sc == 403:
                # Try login and do again
                if not is_repeat:
                    self.login()
                    return self.call(call, parameters = parameters, is_repeat = True, **kwargs)

            log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))
        except:
            log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

        return {}

    def getApiLevel(self):

        if not self.api_level:

            try:
                data = self.call('app/apilevel', auth = False)
                self.api_level = float(data.get('apilevel'))
            except HTTPError as e:
                sc = e.response.status_code
                if sc == 403:
                    log.error('This version of NZBVortex isn\'t supported. Please update to 2.8.6 or higher')
                else:
                    log.error('NZBVortex doesn\'t seem to be running or maybe the remote option isn\'t enabled yet: %s', traceback.format_exc(1))

        return self.api_level

    def isEnabled(self, manual = False, data = None):
        if not data: data = {}
        return super(NZBVortex, self).isEnabled(manual, data) and self.getApiLevel()


config = [{
    'name': 'nzbvortex',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'nzbvortex',
            'label': 'NZBVortex',
            'description': 'Use <a href="https://www.nzbvortex.com/" target="_blank">NZBVortex</a> to download NZBs.',
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
                    'default': 'https://localhost:4321',
                    'description': 'Hostname with port. Usually <strong>https://localhost:4321</strong>',
                },
                {
                    'name': 'api_key',
                    'label': 'Api Key',
                },
                {
                    'name': 'group',
                    'label': 'Group',
                    'description': 'The group CP places the nzb in. Make sure to create it in NZBVortex.',
                },
                {
                    'name': 'manual',
                    'default': False,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Disable this downloader for automated searches, but use it when I manually send a release.',
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

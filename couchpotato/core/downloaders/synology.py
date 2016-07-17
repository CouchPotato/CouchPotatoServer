import json
import traceback

from couchpotato.core._base.downloader.main import DownloaderBase
from couchpotato.core.helpers.encoding import isInt
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
import requests


log = CPLog(__name__)

autoload = 'Synology'


class Synology(DownloaderBase):

    protocol = ['nzb', 'torrent', 'torrent_magnet']
    status_support = False

    def download(self, data = None, media = None, filedata = None):
        """
        Send a torrent/nzb file to the downloader

        :param data: dict returned from provider
            Contains the release information
        :param media: media dict with information
            Used for creating the filename when possible
        :param filedata: downloaded torrent/nzb filedata
            The file gets downloaded in the searcher and send to this function
            This is done to have fail checking before using the downloader, so the downloader
            doesn't need to worry about that
        :return: boolean
            One fail returns false, but the downloader should log his own errors
        """

        if not media: media = {}
        if not data: data = {}

        response = False
        log.info('Sending "%s" (%s) to Synology.', (data['name'], data['protocol']))

        # Load host from config and split out port.
        host = cleanHost(self.conf('host'), protocol = False).split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        try:
            # Send request to Synology
            srpc = SynologyRPC(host[0], host[1], self.conf('username'), self.conf('password'), self.conf('destination'))
            if data['protocol'] == 'torrent_magnet':
                log.info('Adding torrent URL %s', data['url'])
                response = srpc.create_task(url = data['url'])
            elif data['protocol'] in ['nzb', 'torrent']:
                log.info('Adding %s' % data['protocol'])
                if not filedata:
                    log.error('No %s data found', data['protocol'])
                else:
                    filename = data['name'] + '.' + data['protocol']
                    response = srpc.create_task(filename = filename, filedata = filedata)
        except:
            log.error('Exception while adding torrent: %s', traceback.format_exc())
        finally:
            return self.downloadReturnId('') if response else False

    def test(self):
        """ Check if connection works
        :return: bool
        """

        host = cleanHost(self.conf('host'), protocol = False).split(':')
        try:
            srpc = SynologyRPC(host[0], host[1], self.conf('username'), self.conf('password'))
            test_result = srpc.test()
        except:
            return False

        return test_result

    def getEnabledProtocol(self):
        if self.conf('use_for') == 'both':
            return super(Synology, self).getEnabledProtocol()
        elif self.conf('use_for') == 'torrent':
            return ['torrent', 'torrent_magnet']
        else:
            return ['nzb']

    def isEnabled(self, manual = False, data = None):
        if not data: data = {}

        for_protocol = ['both']
        if data and 'torrent' in data.get('protocol'):
            for_protocol.append('torrent')
        elif data:
            for_protocol.append(data.get('protocol'))

        return super(Synology, self).isEnabled(manual, data) and\
               ((self.conf('use_for') in for_protocol))


class SynologyRPC(object):

    """SynologyRPC lite library"""

    def __init__(self, host = 'localhost', port = 5000, username = None, password = None, destination = None):

        super(SynologyRPC, self).__init__()

        self.download_url = 'http://%s:%s/webapi/DownloadStation/task.cgi' % (host, port)
        self.auth_url = 'http://%s:%s/webapi/auth.cgi' % (host, port)
        self.sid = None
        self.username = username
        self.password = password
        self.destination = destination
        self.session_name = 'DownloadStation'

    def _login(self):
        if self.username and self.password:
            args = {'api': 'SYNO.API.Auth', 'account': self.username, 'passwd': self.password, 'version': 2,
            'method': 'login', 'session': self.session_name, 'format': 'sid'}
            response = self._req(self.auth_url, args)
            if response['success']:
                self.sid = response['data']['sid']
                log.debug('sid=%s', self.sid)
            else:
                log.error('Couldn\'t log into Synology, %s', response)
            return response['success']
        else:
            log.error('User or password missing, not using authentication.')
            return False

    def _logout(self):
        args = {'api':'SYNO.API.Auth', 'version':1, 'method':'logout', 'session':self.session_name, '_sid':self.sid}
        return self._req(self.auth_url, args)

    def _req(self, url, args, files = None):
        response = {'success': False}
        try:
            req = requests.post(url, data = args, files = files, verify = False)
            req.raise_for_status()
            response = json.loads(req.text)
            if response['success']:
                log.info('Synology action successfull')
            return response
        except requests.ConnectionError as err:
            log.error('Synology connection error, check your config %s', err)
        except requests.HTTPError as err:
            log.error('SynologyRPC HTTPError: %s', err)
        except Exception as err:
            log.error('Exception: %s', err)
        finally:
            return response

    def create_task(self, url = None, filename = None, filedata = None):
        """ Creates new download task in Synology DownloadStation. Either specify
        url or pair (filename, filedata).

        Returns True if task was created, False otherwise
        """
        result = False
        # login
        if self._login():
            args = {'api': 'SYNO.DownloadStation.Task',
                    'version': '1',
                    'method': 'create',
                    '_sid': self.sid}

            if self.destination and len(self.destination) > 0:
                args['destination'] = self.destination

            if url:
                log.info('Login success, adding torrent URI')
                args['uri'] = url
                response = self._req(self.download_url, args = args)
                if response['success']:
                    log.info('Response: %s', response)
                else:
                    log.error('Response: %s', response)
                    synoerrortype = {
                        400 : 'File upload failed',
                        401 : 'Max number of tasks reached',
                        402 : 'Destination denied',
                        403 : 'Destination does not exist',
                        404 : 'Invalid task id',
                        405 : 'Invalid task action',
                        406 : 'No default destination',
                        407 : 'Set destination failed',
                        408 : 'File does not exist'
                    }
                    log.error('DownloadStation returned the following error : %s', synoerrortype[response['error']['code']])
                result = response['success']
            elif filename and filedata:
                log.info('Login success, adding torrent')
                files = {'file': (filename, filedata)}
                response = self._req(self.download_url, args = args, files = files)
                log.info('Response: %s', response)
                result = response['success']
            else:
                log.error('Invalid use of SynologyRPC.create_task: either url or filename+filedata must be specified')
            self._logout()

        return result

    def test(self):
        return bool(self._login())


config = [{
    'name': 'synology',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'synology',
            'label': 'Synology',
            'description': 'Use <a href="https://www.synology.com/en-us/dsm/app_packages/DownloadStation" target="_blank">Synology Download Station</a> to download.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'nzb,torrent',
                },
                {
                    'name': 'host',
                    'default': 'localhost:5000',
                    'description': 'Hostname with port. Usually <strong>localhost:5000</strong>',
                },
                {
                    'name': 'username',
                },
                {
                    'name': 'password',
                    'type': 'password',
                },
                {
                    'name': 'destination',
                    'description': 'Specify <strong>existing</strong> destination share to where your files will be downloaded, usually <strong>Downloads</strong>',
                    'advanced': True,
                },
                {
                    'name': 'use_for',
                    'label': 'Use for',
                    'default': 'both',
                    'type': 'dropdown',
                    'values': [('usenet & torrents', 'both'), ('usenet', 'nzb'), ('torrent', 'torrent')],
                },
                {
                    'name': 'manual',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Disable this downloader for automated searches, but use it when I manually send a release.',
                },
            ],
        }
    ],
}]

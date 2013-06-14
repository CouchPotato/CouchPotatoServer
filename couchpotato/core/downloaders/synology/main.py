from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import isInt
from couchpotato.core.logger import CPLog
import json
import requests

log = CPLog(__name__)


class Synology(Downloader):

    type = ['torrent', 'torrent_magnet']
    log = CPLog(__name__)

    def download(self, data, movie, filedata = None):

        response = False
        log.error('Sending "%s" (%s) to Synology.', (data['name'], data['type']))

        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        try:
            # Send request to Synology
            srpc = SynologyRPC(host[0], host[1], self.conf('username'), self.conf('password'))
            if data['type'] == 'torrent_magnet':
                log.info('Adding torrent URL %s', data['url'])
                response = srpc.create_task(url = data['url'])
            elif data['type'] == 'torrent':
                log.info('Adding torrent')
                if not filedata:
                    log.error('No torrent data found')
                else:
                    filename = data['name'] + '.' + data['type']
                    response = srpc.create_task(filename = filename, filedata = filedata)
        except Exception, err:
            log.error('Exception while adding torrent: %s', err)
        finally:
            return response


class SynologyRPC(object):

    '''SynologyRPC lite library'''

    def __init__(self, host = 'localhost', port = 5000, username = None, password = None):

        super(SynologyRPC, self).__init__()

        self.download_url = 'http://%s:%s/webapi/DownloadStation/task.cgi' % (host, port)
        self.auth_url = 'http://%s:%s/webapi/auth.cgi' % (host, port)
        self.username = username
        self.password = password
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
                log.error('Couldn\'t login to Synology, %s', response)
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
            req = requests.post(url, data = args, files = files)
            req.raise_for_status()
            response = json.loads(req.text)
            if response['success'] == True:
                log.info('Synology action successfull')
            return response
        except requests.ConnectionError, err:
            log.error('Synology connection error, check your config %s', err)
        except requests.HTTPError, err:
            log.error('SynologyRPC HTTPError: %s', err)
        except Exception, err:
            log.error('Exception: %s', err)
        finally:
            return response

    def create_task(self, url = None, filename = None, filedata = None):
        ''' Creates new download task in Synology DownloadStation. Either specify
        url or pair (filename, filedata).

        Returns True if task was created, False otherwise
        '''
        result = False
        # login
        if self._login():
            args = {'api': 'SYNO.DownloadStation.Task',
                    'version': '1',
                    'method': 'create',
                    '_sid': self.sid}
            if url:
                log.info('Login success, adding torrent URI')
                args['uri'] = url
                response = self._req(self.download_url, args = args)
                log.info('Response: %s', response)
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

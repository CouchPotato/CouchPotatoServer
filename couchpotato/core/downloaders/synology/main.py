from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import isInt
from couchpotato.core.logger import CPLog
import httplib
import json
import urllib
import urllib2


log = CPLog(__name__)

class Synology(Downloader):

    type = ['torrent_magnet']
    log = CPLog(__name__)

    def download(self, data, movie, manual = False, filedata = None):

        if self.isDisabled(manual) or not self.isCorrectType(data.get('type')):
            return

        log.error('Sending "%s" (%s) to Synology.', (data.get('name'), data.get('type')))

        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        if data.get('type') == 'torrent':
            log.error('Can\'t add binary torrent file')
            return False

        try:
            # Send request to Transmission
            srpc = SynologyRPC(host[0], host[1], self.conf('username'), self.conf('password'))
            remote_torrent = srpc.add_torrent_uri(data.get('url'))
            log.info('Response: %s', remote_torrent)
            return remote_torrent['success']
        except Exception, err:
            log.error('Exception while adding torrent: %s', err)
            return False


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
            if response['success'] == True:
                self.sid = response['data']['sid']
                log.debug('Sid=%s', self.sid)
            return response
        elif self.username or self.password:
            log.error('User or password missing, not using authentication.')
            return False

    def _logout(self):
        args = {'api':'SYNO.API.Auth', 'version':1, 'method':'logout', 'session':self.session_name, '_sid':self.sid}
        return self._req(self.auth_url, args)

    def _req(self, url, args):
        req_url = url + '?' + urllib.urlencode(args)
        try:
            req_open = urllib2.urlopen(req_url)
            response = json.loads(req_open.read())
            if response['success'] == True:
                log.info('Synology action successfull')
            return response
        except httplib.InvalidURL, err:
            log.error('Invalid Transmission host, check your config %s', err)
            return False
        except urllib2.HTTPError, err:
            log.error('SynologyRPC HTTPError: %s', err)
            return False
        except urllib2.URLError, err:
            log.error('Unable to connect to Synology %s', err)
            return False

    def add_torrent_uri(self, torrent):
        log.info('Adding torrent URL %s', torrent)
        response = {}
        # login
        login = self._login()
        if len(login) > 0 and login['success'] == True:
            log.info('Login success, adding torrent')
            args = {'api':'SYNO.DownloadStation.Task', 'version':1, 'method':'create', 'uri':torrent, '_sid':self.sid}
            response = self._req(self.download_url, args)
            self._logout()
        else:
            log.error('Couldn\'t login to Synology, %s', login)
        return response



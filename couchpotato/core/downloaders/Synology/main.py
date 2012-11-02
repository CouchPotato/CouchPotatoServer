from base64 import b64encode
from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import isInt
from couchpotato.core.logger import CPLog
import httplib
import json
import os.path
import re
import urllib2
import urllib

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
            log.info("Response: %s", remote_torrent)
            return remote_torrent['success']
        except Exception, err:
            log.error("Exception while adding torrent: %s", err)
            return False


class SynologyRPC(object):

    """SynologyRPC lite library"""

    def __init__(self, host = 'localhost', port = 5000, username = None, password = None):

        super(SynologyRPC, self).__init__()

        self.DLurl    = 'http://' + host + ':' + str(port) + '/webapi/DownloadStation/task.cgi'
        self.Authurl  = 'http://' + host + ':' + str(port) + '/webapi/auth.cgi'
        self.username = username
        self.password = password
        self.session_name = "DownloadStation"
        if username and password:
            if self._login() == True:
                log.info( ">Login ok" )
            else:
                log.error( ">Login failed" )
        elif username or password:
            log.error('User or password missing, not using authentication.')

    def _login(self):
        args = {'api': 'SYNO.API.Auth', 'account': self.username, 'passwd': self.password, 'version': 2, 
            'method': 'login', 'session': self.session_name, 'format': 'sid'}
        response = self._req(self.Authurl, args)
        if response['success'] == True:
            self.sid = response['data']['sid']
            log.info( "Sid=%s", self.sid)
        return response['success']

    def _logout(self):
        args = {'api':'SYNO.API.Auth', 'version':1, 'method':'logout', 'session':self.session_name}
        response = self._req(self.Authurl, args)
        return response['success']

    def _req(self, url, args):
        req_url = url + '?' + urllib.urlencode(args)
        #print "Trying URL: ", req_url
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
        log.info( "Adding torrent URL %s", torrent)
        args = {'api':'SYNO.DownloadStation.Task', 'version':1, 'method':'create', 'uri':torrent, '_sid':self.sid}
        response = self._req(self.DLurl, args)
        return response


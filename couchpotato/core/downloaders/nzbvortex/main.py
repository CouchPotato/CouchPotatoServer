from base64 import b64encode
from couchpotato.core.downloaders.base import Downloader, ReleaseDownloadList
from couchpotato.core.helpers.encoding import tryUrlencode, sp
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from urllib2 import URLError
from uuid import uuid4
import hashlib
import httplib
import json
import socket
import ssl
import sys
import traceback
import urllib2

log = CPLog(__name__)


class NZBVortex(Downloader):

    protocol = ['nzb']
    api_level = None
    session_id = None

    def download(self, data = None, movie = None, filedata = None):
        if not movie: movie = {}
        if not data: data = {}

        # Send the nzb
        try:
            nzb_filename = self.createFileName(data, filedata, movie)
            self.call('nzb/add', params = {'file': (nzb_filename, filedata)}, multipart = True)

            raw_statuses = self.call('nzb')
            nzb_id = [nzb['id'] for nzb in raw_statuses.get('nzbs', []) if nzb['name'] == nzb_filename][0]
            return self.downloadReturnId(nzb_id)
        except:
            log.error('Something went wrong sending the NZB file: %s', traceback.format_exc())
            return False

    def getAllDownloadStatus(self):

        raw_statuses = self.call('nzb')

        release_downloads = ReleaseDownloadList(self)
        for nzb in raw_statuses.get('nzbs', []):

            # Check status
            status = 'busy'
            if nzb['state'] == 20:
                status = 'completed'
            elif nzb['state'] in [21, 22, 24]:
                status = 'failed'

            release_downloads.append({
                'id': nzb['id'],
                'name': nzb['uiTitle'],
                'status': status,
                'original_status': nzb['state'],
                'timeleft':-1,
                'folder': sp(nzb['destinationPath']),
            })

        return release_downloads

    def removeFailed(self, release_download):

        log.info('%s failed downloading, deleting...', release_download['name'])

        try:
            self.call('nzb/%s/cancel' % release_download['id'])
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


    def call(self, call, parameters = None, repeat = False, auth = True, *args, **kwargs):

        # Login first
        if not parameters: parameters = {}
        if not self.session_id and auth:
            self.login()

        # Always add session id to request
        if self.session_id:
            parameters['sessionid'] = self.session_id

        params = tryUrlencode(parameters)

        url = cleanHost(self.conf('host')) + 'api/' + call
        url_opener = urllib2.build_opener(HTTPSHandler())

        try:
            data = self.urlopen('%s?%s' % (url, params), opener = url_opener, *args, **kwargs)

            if data:
                return json.loads(data)
        except URLError, e:
            if hasattr(e, 'code') and e.code == 403:
                # Try login and do again
                if not repeat:
                    self.login()
                    return self.call(call, parameters = parameters, repeat = True, **kwargs)

            log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))
        except:
            log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))

        return {}

    def getApiLevel(self):

        if not self.api_level:

            url = cleanHost(self.conf('host')) + 'api/app/apilevel'
            url_opener = urllib2.build_opener(HTTPSHandler())

            try:
                data = self.urlopen(url, opener = url_opener, show_error = False)
                self.api_level = float(json.loads(data).get('apilevel'))
            except URLError, e:
                if hasattr(e, 'code') and e.code == 403:
                    log.error('This version of NZBVortex isn\'t supported. Please update to 2.8.6 or higher')
                else:
                    log.error('NZBVortex doesn\'t seem to be running or maybe the remote option isn\'t enabled yet: %s', traceback.format_exc(1))

        return self.api_level

    def isEnabled(self, manual = False, data = None):
        if not data: data = {}
        return super(NZBVortex, self).isEnabled(manual, data) and self.getApiLevel()


class HTTPSConnection(httplib.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        httplib.HTTPSConnection.__init__(self, *args, **kwargs)

    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if sys.version_info < (2, 6, 7):
            if hasattr(self, '_tunnel_host'):
                self.sock = sock
                self._tunnel()
        else:
            if self._tunnel_host:
                self.sock = sock
                self._tunnel()

        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version = ssl.PROTOCOL_TLSv1)

class HTTPSHandler(urllib2.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(HTTPSConnection, req)

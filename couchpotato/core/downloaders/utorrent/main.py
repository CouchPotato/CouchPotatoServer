from base64 import b64encode
from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import isInt
from couchpotato.core.logger import CPLog
import httplib
import json
import os.path
import re
import urllib
import urllib2
import time
import cookielib

log = CPLog(__name__)


class uTorrent(Downloader):

    type = ['torrent_magnet']
    utAPI = None

    def download(self, data, movie, manual = False, filedata = None):

        if self.isDisabled(manual) or not self.isCorrectType(data.get('type')):
            return

        log.debug('Sending "%s" (%s) to uTorrent.', (data.get('name'), data.get('type')))

        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        torrent_params = {}
        if self.conf('label'):
            torrent_params['label'] = self.conf('label')
        
        if not filedata and data.get('type') == 'torrent':
            log.error('Failed sending torrent, no data')
            return False

        torrent_hash = re.findall('urn:btih:([\w]{32,40})', data.get('url'))[0]
        # Send request to uTorrent
        try:
            if not self.utAPI:
                self.utAPI = uTorrentAPI(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))
            self.utAPI.add_torrent_uri(data.get('url'))

            # Change settings of added torrents
            self.utAPI.set_torrent(torrent_hash, torrent_params)
            if self.conf('paused', default = 0):
                self.utAPI.pause_torrent(torrent_hash)
            return True
        except Exception, err:
            log.error('Failed to change settings for transfer: %s', err)
            return False


class uTorrentAPI(object):

    def __init__(self, host = 'localhost', port = 8000, username = None, password = None):

        super(uTorrentAPI, self).__init__()

        self.url = 'http://' + host + ':' + str(port) + '/gui/'
        self.token = ''
        self.last_time = time.time()
        cookies = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
        self.opener.addheaders = [('User-agent', 'couchpotato-utorrent-client/1.0')]
        if username and password:
            password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(realm = None, uri = self.url, user = username, passwd = password)
            self.opener.add_handler(urllib2.HTTPBasicAuthHandler(password_manager))
            self.opener.add_handler(urllib2.HTTPDigestAuthHandler(password_manager))
        elif username or password:
            log.debug('User or password missing, not using authentication.')
        self.token = self.get_token()

    def _request(self, action):
        if time.time() > self.last_time + 1800:
            self.last_time = time.time()
            self.token = self.get_token()
        request = urllib2.Request(self.url + "?token=" + self.token + "&" + action)
        try:
            open_request = self.opener.open(request)
            response = open_request.read()
            log.debug('response: %s', response)
            if response:
                log.debug('uTorrent action successfull')
                return response
            else:
                log.debug('Unknown failure sending command to uTorrent. Return text is: %s', response)
                return False
        except httplib.InvalidURL, err:
            log.error('Invalid uTorrent host, check your config %s', err)
            return False
        except urllib2.HTTPError, err:
            if err.code == 401:
                log.error('Invalid uTorrent Username or Password, check your config')
                return False
            else:
                log.error('uTorrent HTTPError: %s', err)
        except urllib2.URLError, err:
            log.error('Unable to connect to uTorrent %s', err)

    def get_token(self):
        request = self.opener.open(self.url+"token.html")
        token = re.findall("<div.*?>(.*?)</", request.read())[0]
        return token

    def add_torrent_uri(self, torrent):
        action = "action=add-url&s=%s" % urllib.quote(torrent)
        return self._request(action)

    def set_torrent(self, hash, params):
        action = "action=setprops&hash=%s" % hash
        for k, v in params.iteritems():
            action += "&s=%s&v=%s" % (k, v)
        return self._request(action)

    def pause_torrent(self, hash):
        action = "action=pause&hash=%s" % hash
        return self._request(action)
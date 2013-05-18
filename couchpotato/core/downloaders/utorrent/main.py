from base64 import b16encode, b32decode
from bencode import bencode, bdecode
from couchpotato.core.downloaders.base import Downloader, StatusList
from couchpotato.core.helpers.encoding import isInt, ss
from couchpotato.core.logger import CPLog
from datetime import timedelta
from hashlib import sha1
from multipartpost import MultipartPostHandler
import cookielib
import httplib
import json
import os
import re
import time
import urllib
import urllib2


log = CPLog(__name__)


class uTorrent(Downloader):

    type = ['torrent', 'torrent_magnet']
    utorrent_api = None

    def download(self, data, movie, filedata = None):

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

        if data.get('type') == 'torrent_magnet':
            torrent_hash = re.findall('urn:btih:([\w]{32,40})', data.get('url'))[0].upper()
            torrent_params['trackers'] = '%0D%0A%0D%0A'.join(self.torrent_trackers)
        else:
            info = bdecode(filedata)["info"]
            torrent_hash = sha1(bencode(info)).hexdigest().upper()
            torrent_filename = self.createFileName(data, filedata, movie)

        # Convert base 32 to hex
        if len(torrent_hash) == 32:
            torrent_hash = b16encode(b32decode(torrent_hash))

        # Send request to uTorrent
        try:
            if not self.utorrent_api:
                self.utorrent_api = uTorrentAPI(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))

            if data.get('type') == 'torrent_magnet':
                self.utorrent_api.add_torrent_uri(data.get('url'))
            else:
                self.utorrent_api.add_torrent_file(torrent_filename, filedata)

            # Change settings of added torrents
            self.utorrent_api.set_torrent(torrent_hash, torrent_params)
            if self.conf('paused', default = 0):
                self.utorrent_api.pause_torrent(torrent_hash)
            return self.downloadReturnId(torrent_hash)
        except Exception, err:
            log.error('Failed to send torrent to uTorrent: %s', err)
            return False

    def getAllDownloadStatus(self):

        log.debug('Checking uTorrent download status.')

        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        try:
            self.utorrent_api = uTorrentAPI(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))
        except Exception, err:
            log.error('Failed to get uTorrent object: %s', err)
            return False

        data = ''
        try:
            data = self.utorrent_api.get_status()
            queue = json.loads(data)
            if queue.get('error'):
                log.error('Error getting data from uTorrent: %s', queue.get('error'))
                return False

        except Exception, err:
            log.error('Failed to get status from uTorrent: %s', err)
            return False

        if queue.get('torrents', []) == []:
            log.debug('Nothing in queue')
            return False

        statuses = StatusList(self)
        download_folder = ''
        settings_dict = {}

        try:
            data = self.utorrent_api.get_settings()
            utorrent_settings = json.loads(data)

            # Create settings dict
            for item in utorrent_settings['settings']:
                if item[1] == 0: # int
                    settings_dict[item[0]] = int(item[2] if not item[2].strip() == '' else '0')
                elif item[1] == 1: # bool
                    settings_dict[item[0]] = True if item[2] == 'true' else False
                elif item[1] == 2: # string
                    settings_dict[item[0]] = item[2]

            log.debug('uTorrent settings: %s, %s', (settings_dict['dir_completed_download_flag'], settings_dict['dir_active_download_flag']))

            # Get the download path from the uTorrent settings
            if settings_dict['dir_completed_download_flag']:
                download_folder = settings_dict['dir_completed_download']
            elif settings_dict['dir_active_download_flag']:
                download_folder = settings_dict['dir_active_download']
            else:
                log.info('No download folder set in uTorrent. Please set a download folder')
                return False

        except Exception, err:
            log.error('Failed to get settings from uTorrent: %s', err)
            return False

        # Get torrents
        for item in queue.get('torrents', []):

            # item[21] = Paused | Downloading | Seeding | Finished
            status = 'busy'
            if item[21] == 'Finished' or item[21] == 'Seeding':
                status = 'completed'

            if settings_dict['dir_add_label']:
                release_folder = os.path.join(download_folder, item[11], item[2])
            else:
                release_folder = os.path.join(download_folder, item[2])

            statuses.append({
                'id': item[0],
                'name': item[2],
                'status':  status,
                'original_status': item[1],
                'timeleft': str(timedelta(seconds = item[10])),
                'folder': release_folder,
            })

        return statuses



class uTorrentAPI(object):

    def __init__(self, host = 'localhost', port = 8000, username = None, password = None):

        super(uTorrentAPI, self).__init__()

        self.url = 'http://' + str(host) + ':' + str(port) + '/gui/'
        self.token = ''
        self.last_time = time.time()
        cookies = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies), MultipartPostHandler)
        self.opener.addheaders = [('User-agent', 'couchpotato-utorrent-client/1.0')]
        if username and password:
            password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(realm = None, uri = self.url, user = username, passwd = password)
            self.opener.add_handler(urllib2.HTTPBasicAuthHandler(password_manager))
            self.opener.add_handler(urllib2.HTTPDigestAuthHandler(password_manager))
        elif username or password:
            log.debug('User or password missing, not using authentication.')
        self.token = self.get_token()

    def _request(self, action, data = None):
        if time.time() > self.last_time + 1800:
            self.last_time = time.time()
            self.token = self.get_token()
        request = urllib2.Request(self.url + "?token=" + self.token + "&" + action, data)
        try:
            open_request = self.opener.open(request)
            response = open_request.read()
            if response:
                return response
            else:
                log.debug('Unknown failure sending command to uTorrent. Return text is: %s', response)
        except httplib.InvalidURL, err:
            log.error('Invalid uTorrent host, check your config %s', err)
        except urllib2.HTTPError, err:
            if err.code == 401:
                log.error('Invalid uTorrent Username or Password, check your config')
            else:
                log.error('uTorrent HTTPError: %s', err)
        except urllib2.URLError, err:
            log.error('Unable to connect to uTorrent %s', err)
        return False

    def get_token(self):
        request = self.opener.open(self.url + "token.html")
        token = re.findall("<div.*?>(.*?)</", request.read())[0]
        return token

    def add_torrent_uri(self, torrent):
        action = "action=add-url&s=%s" % urllib.quote(torrent)
        return self._request(action)

    def add_torrent_file(self, filename, filedata):
        action = "action=add-file"
        return self._request(action, {"torrent_file": (ss(filename), filedata)})

    def set_torrent(self, hash, params):
        action = "action=setprops&hash=%s" % hash
        for k, v in params.iteritems():
            action += "&s=%s&v=%s" % (k, v)
        return self._request(action)

    def pause_torrent(self, hash):
        action = "action=pause&hash=%s" % hash
        return self._request(action)

    def get_status(self):
        action = "list=1"
        return self._request(action)

    def get_settings(self):
        action = "action=getsettings"
        return self._request(action)

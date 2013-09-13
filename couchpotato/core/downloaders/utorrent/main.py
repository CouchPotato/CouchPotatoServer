from base64 import b16encode, b32decode
from bencode import bencode as benc, bdecode
from couchpotato.core.downloaders.base import Downloader, StatusList
from couchpotato.core.helpers.encoding import isInt, ss
from couchpotato.core.helpers.variable import tryInt, tryFloat
from couchpotato.core.logger import CPLog
from datetime import timedelta
from hashlib import sha1
from multipartpost import MultipartPostHandler
import cookielib
import httplib
import json
import os
import re
import stat
import time
import urllib
import urllib2

log = CPLog(__name__)


class uTorrent(Downloader):

    protocol = ['torrent', 'torrent_magnet']
    utorrent_api = None

    def connect(self):
        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        self.utorrent_api = uTorrentAPI(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))

        return self.utorrent_api

    def download(self, data = None, movie = None, filedata = None):
        if not movie: movie = {}
        if not data: data = {}

        log.debug('Sending "%s" (%s) to uTorrent.', (data.get('name'), data.get('protocol')))

        if not self.connect():
            return False

        settings = self.utorrent_api.get_settings()
        if not settings:
            return False

        #Fix settings in case they are not set for CPS compatibility
        new_settings = {}
        if not (settings.get('seed_prio_limitul') == 0 and settings['seed_prio_limitul_flag']):
            new_settings['seed_prio_limitul'] = 0
            new_settings['seed_prio_limitul_flag'] = True
            log.info('Updated uTorrent settings to set a torrent to complete after it the seeding requirements are met.')

        if settings.get('bt.read_only_on_complete'): #This doesn't work as this option seems to be not available through the api. Mitigated with removeReadOnly function
            new_settings['bt.read_only_on_complete'] = False
            log.info('Updated uTorrent settings to not set the files to read only after completing.')

        if new_settings:
            self.utorrent_api.set_settings(new_settings)

        torrent_params = {}
        if self.conf('label'):
            torrent_params['label'] = self.conf('label')

        if not filedata and data.get('protocol') == 'torrent':
            log.error('Failed sending torrent, no data')
            return False

        if data.get('protocol') == 'torrent_magnet':
            torrent_hash = re.findall('urn:btih:([\w]{32,40})', data.get('url'))[0].upper()
            torrent_params['trackers'] = '%0D%0A%0D%0A'.join(self.torrent_trackers)
        else:
            info = bdecode(filedata)["info"]
            torrent_hash = sha1(benc(info)).hexdigest().upper()
            torrent_filename = self.createFileName(data, filedata, movie)

        if data.get('seed_ratio'):
            torrent_params['seed_override'] = 1
            torrent_params['seed_ratio'] = tryInt(tryFloat(data['seed_ratio']) * 1000)

        if data.get('seed_time'):
            torrent_params['seed_override'] = 1
            torrent_params['seed_time'] = tryInt(data['seed_time']) * 3600

        # Convert base 32 to hex
        if len(torrent_hash) == 32:
            torrent_hash = b16encode(b32decode(torrent_hash))

        # Send request to uTorrent
        if data.get('protocol') == 'torrent_magnet':
            self.utorrent_api.add_torrent_uri(data.get('url'))
        else:
            self.utorrent_api.add_torrent_file(torrent_filename, filedata)

        # Change settings of added torrent
        self.utorrent_api.set_torrent(torrent_hash, torrent_params)
        if self.conf('paused', default = 0):
            self.utorrent_api.pause_torrent(torrent_hash)

        return self.downloadReturnId(torrent_hash)

    def getAllDownloadStatus(self):

        log.debug('Checking uTorrent download status.')

        if not self.connect():
            return False

        statuses = StatusList(self)

        data = self.utorrent_api.get_status()
        if not data:
            log.error('Error getting data from uTorrent')
            return False

        queue = json.loads(data)
        if queue.get('error'):
            log.error('Error getting data from uTorrent: %s', queue.get('error'))
            return False

        if not queue.get('torrents'):
            log.debug('Nothing in queue')
            return False

        # Get torrents
        for item in queue['torrents']:

            # item[21] = Paused | Downloading | Seeding | Finished
            status = 'busy'
            if 'Finished' in item[21]:
                status = 'completed'
                self.removeReadOnly(item[26])
            elif 'Seeding' in item[21]:
                status = 'seeding'
                self.removeReadOnly(item[26])

            statuses.append({
                'id': item[0],
                'name': item[2],
                'status':  status,
                'seed_ratio': float(item[7]) / 1000,
                'original_status': item[1],
                'timeleft': str(timedelta(seconds = item[10])),
                'folder': ss(item[26]),
            })

        return statuses

    def pause(self, item, pause = True):
        if not self.connect():
            return False
        return self.utorrent_api.pause_torrent(item['id'], pause)

    def removeFailed(self, item):
        log.info('%s failed downloading, deleting...', item['name'])
        if not self.connect():
            return False
        return self.utorrent_api.remove_torrent(item['id'], remove_data = True)

    def processComplete(self, item, delete_files = False):
        log.debug('Requesting uTorrent to remove the torrent %s%s.', (item['name'], ' and cleanup the downloaded files' if delete_files else ''))
        if not self.connect():
            return False
        return self.utorrent_api.remove_torrent(item['id'], remove_data = delete_files)
    
    def removeReadOnly(self, folder):
        #Removes all read-only flags in a folder
        if folder and os.path.isdir(folder):
            for root, folders, filenames in os.walk(folder):
                for filename in filenames:
                    os.chmod(os.path.join(root, filename), stat.S_IWRITE)

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

    def pause_torrent(self, hash, pause = True):
        if pause:
            action = "action=pause&hash=%s" % hash
        else:
            action = "action=unpause&hash=%s" % hash
        return self._request(action)

    def stop_torrent(self, hash):
        action = "action=stop&hash=%s" % hash
        return self._request(action)

    def remove_torrent(self, hash, remove_data = False):
        if remove_data:
            action = "action=removedata&hash=%s" % hash
        else:
            action = "action=remove&hash=%s" % hash
        return self._request(action)

    def get_status(self):
        action = "list=1"
        return self._request(action)

    def get_settings(self):
        action = "action=getsettings"
        settings_dict = {}
        try:
            utorrent_settings = json.loads(self._request(action))

            # Create settings dict
            for item in utorrent_settings['settings']:
                if item[1] == 0: # int
                    settings_dict[item[0]] = int(item[2] if not item[2].strip() == '' else '0')
                elif item[1] == 1: # bool
                    settings_dict[item[0]] = True if item[2] == 'true' else False
                elif item[1] == 2: # string
                    settings_dict[item[0]] = item[2]

            #log.debug('uTorrent settings: %s', settings_dict)

        except Exception, err:
            log.error('Failed to get settings from uTorrent: %s', err)

        return settings_dict

    def set_settings(self, settings_dict = None):
        if not settings_dict: settings_dict = {}

        for key in settings_dict:
            if isinstance(settings_dict[key], bool):
                settings_dict[key] = 1 if settings_dict[key] else 0

        action = 'action=setsetting' + ''.join(['&s=%s&v=%s' % (key, value) for (key, value) in settings_dict.items()])
        return self._request(action)

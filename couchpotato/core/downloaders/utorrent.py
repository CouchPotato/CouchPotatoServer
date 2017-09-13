from base64 import b16encode, b32decode
from datetime import timedelta
from hashlib import sha1
import cookielib
import httplib
import json
import os
import re
import stat
import time
import urllib
import urllib2

from bencode import bencode as benc, bdecode
from couchpotato.core._base.downloader.main import DownloaderBase, ReleaseDownloadList
from couchpotato.core.helpers.encoding import isInt, ss, sp
from couchpotato.core.helpers.variable import tryInt, tryFloat, cleanHost
from couchpotato.core.logger import CPLog
from multipartpost import MultipartPostHandler


log = CPLog(__name__)

autoload = 'uTorrent'


class uTorrent(DownloaderBase):

    protocol = ['torrent', 'torrent_magnet']
    utorrent_api = None
    status_flags = {
        'STARTED': 1,
        'CHECKING': 2,
        'CHECK-START': 4,
        'CHECKED': 8,
        'ERROR': 16,
        'PAUSED': 32,
        'QUEUED': 64,
        'LOADED': 128
    }

    def connect(self):
        # Load host from config and split out port.
        host = cleanHost(self.conf('host'), protocol = False).split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        self.utorrent_api = uTorrentAPI(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))

        return self.utorrent_api

    def download(self, data = None, media = None, filedata = None):
        """
        Send a torrent/nzb file to the downloader

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

        log.debug("Sending '%s' (%s) to uTorrent.", (data.get('name'), data.get('protocol')))

        if not self.connect():
            return False

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
            info = bdecode(filedata)['info']
            torrent_hash = sha1(benc(info)).hexdigest().upper()

        torrent_filename = self.createFileName(data, filedata, media)

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
            self.utorrent_api.add_torrent_uri(torrent_filename, data.get('url'))
        else:
            self.utorrent_api.add_torrent_file(torrent_filename, filedata)

        # Change settings of added torrent
        self.utorrent_api.set_torrent(torrent_hash, torrent_params)
        if self.conf('paused', default = 0):
            self.utorrent_api.pause_torrent(torrent_hash)

        return self.downloadReturnId(torrent_hash)

    def test(self):
        """ Check if connection works
        :return: bool
        """

        if self.connect():
            build_version = self.utorrent_api.get_build()
            if not build_version:
                return False
            if build_version < 25406:  # This build corresponds to version 3.0.0 stable
                return False, 'Your uTorrent client is too old, please update to newest version.'
            return True

        return False

    def getAllDownloadStatus(self, ids):
        """ Get status of all active downloads

        :param ids: list of (mixed) downloader ids
            Used to match the releases for this downloader as there could be
            other downloaders active that it should ignore
        :return: list of releases
        """

        log.debug('Checking uTorrent download status.')

        if not self.connect():
            return []

        release_downloads = ReleaseDownloadList(self)

        data = self.utorrent_api.get_status()
        if not data:
            log.error('Error getting data from uTorrent')
            return []

        queue = json.loads(data)
        if queue.get('error'):
            log.error('Error getting data from uTorrent: %s', queue.get('error'))
            return []

        if not queue.get('torrents'):
            log.debug('Nothing in queue')
            return []

        # Get torrents
        for torrent in queue['torrents']:
            if torrent[0] in ids:

                #Get files of the torrent
                torrent_files = []
                try:
                    torrent_files = json.loads(self.utorrent_api.get_files(torrent[0]))
                    torrent_files = [sp(os.path.join(torrent[26], torrent_file[0])) for torrent_file in torrent_files['files'][1]]
                except:
                    log.debug('Failed getting files from torrent: %s', torrent[2])

                status = 'busy'
                if (torrent[1] & self.status_flags['STARTED'] or torrent[1] & self.status_flags['QUEUED']) and torrent[4] == 1000:
                    status = 'seeding'
                elif torrent[1] & self.status_flags['ERROR'] and 'There is not enough space on the disk' not in torrent[21]:
                    status = 'failed'
                elif torrent[4] == 1000:
                    status = 'completed'

                if not status == 'busy':
                    self.removeReadOnly(torrent_files)

                release_downloads.append({
                    'id': torrent[0],
                    'name': torrent[2],
                    'status': status,
                    'seed_ratio': float(torrent[7]) / 1000,
                    'original_status': torrent[1],
                    'timeleft': str(timedelta(seconds = torrent[10])),
                    'folder': sp(torrent[26]),
                    'files': torrent_files
                })

        return release_downloads

    def pause(self, release_download, pause = True):
        if not self.connect():
            return False
        return self.utorrent_api.pause_torrent(release_download['id'], pause)

    def removeFailed(self, release_download):
        log.info('%s failed downloading, deleting...', release_download['name'])
        if not self.connect():
            return False
        return self.utorrent_api.remove_torrent(release_download['id'], remove_data = True)

    def processComplete(self, release_download, delete_files = False):
        log.debug('Requesting uTorrent to remove the torrent %s%s.', (release_download['name'], ' and cleanup the downloaded files' if delete_files else ''))
        if not self.connect():
            return False
        return self.utorrent_api.remove_torrent(release_download['id'], remove_data = delete_files)

    def removeReadOnly(self, files):
        #Removes all read-on ly flags in a for all files
        for filepath in files:
            if os.path.isfile(filepath):
                #Windows only needs S_IWRITE, but we bitwise-or with current perms to preserve other permission bits on Linux
                os.chmod(filepath, stat.S_IWRITE | os.stat(filepath).st_mode)

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
        elif username or password:
            log.debug('User or password missing, not using authentication.')
        self.token = self.get_token()

    def _request(self, action, data = None):
        if time.time() > self.last_time + 1800:
            self.last_time = time.time()
            self.token = self.get_token()
        request = urllib2.Request(self.url + '?token=' + self.token + '&' + action, data)
        try:
            open_request = self.opener.open(request)
            response = open_request.read()
            if response:
                return response
            else:
                log.debug('Unknown failure sending command to uTorrent. Return text is: %s', response)
        except httplib.InvalidURL as err:
            log.error('Invalid uTorrent host, check your config %s', err)
        except urllib2.HTTPError as err:
            if err.code == 401:
                log.error('Invalid uTorrent Username or Password, check your config')
            else:
                log.error('uTorrent HTTPError: %s', err)
        except urllib2.URLError as err:
            log.error('Unable to connect to uTorrent %s', err)
        return False

    def get_token(self):
        request = self.opener.open(self.url + 'token.html')
        token = re.findall('<div.*?>(.*?)</', request.read())[0]
        return token

    def add_torrent_uri(self, filename, torrent, add_folder = False):
        action = 'action=add-url&s=%s' % urllib.quote(torrent)
        if add_folder:
            action += '&path=%s' % urllib.quote(filename)
        return self._request(action)

    def add_torrent_file(self, filename, filedata, add_folder = False):
        action = 'action=add-file'
        if add_folder:
            action += '&path=%s' % urllib.quote(filename)
        return self._request(action, {'torrent_file': (ss(filename), filedata)})

    def set_torrent(self, hash, params):
        action = 'action=setprops&hash=%s' % hash
        for k, v in params.items():
            action += '&s=%s&v=%s' % (k, v)
        return self._request(action)

    def pause_torrent(self, hash, pause = True):
        if pause:
            action = 'action=pause&hash=%s' % hash
        else:
            action = 'action=unpause&hash=%s' % hash
        return self._request(action)

    def stop_torrent(self, hash):
        action = 'action=stop&hash=%s' % hash
        return self._request(action)

    def remove_torrent(self, hash, remove_data = False):
        if remove_data:
            action = 'action=removedata&hash=%s' % hash
        else:
            action = 'action=remove&hash=%s' % hash
        return self._request(action)

    def get_status(self):
        action = 'list=1'
        return self._request(action)

    def get_settings(self):
        action = 'action=getsettings'
        settings_dict = {}
        try:
            utorrent_settings = json.loads(self._request(action))

            # Create settings dict
            for setting in utorrent_settings['settings']:
                if setting[1] == 0: # int
                    settings_dict[setting[0]] = int(setting[2] if not setting[2].strip() == '' else '0')
                elif setting[1] == 1: # bool
                    settings_dict[setting[0]] = True if setting[2] == 'true' else False
                elif setting[1] == 2: # string
                    settings_dict[setting[0]] = setting[2]

            #log.debug('uTorrent settings: %s', settings_dict)

        except Exception as err:
            log.error('Failed to get settings from uTorrent: %s', err)

        return settings_dict

    def set_settings(self, settings_dict = None):
        if not settings_dict: settings_dict = {}

        for key in settings_dict:
            if isinstance(settings_dict[key], bool):
                settings_dict[key] = 1 if settings_dict[key] else 0

        action = 'action=setsetting' + ''.join(['&s=%s&v=%s' % (key, value) for (key, value) in settings_dict.items()])
        return self._request(action)

    def get_files(self, hash):
        action = 'action=getfiles&hash=%s' % hash
        return self._request(action)

    def get_build(self):
        data = self._request('')
        if not data:
            return False
        response = json.loads(data)
        return int(response.get('build'))


config = [{
    'name': 'utorrent',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'utorrent',
            'label': 'uTorrent',
            'description': 'Use <a href="http://www.utorrent.com/" target="_blank">uTorrent</a> (3.0+) to download torrents.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'torrent',
                },
                {
                    'name': 'host',
                    'default': 'localhost:8000',
                    'description': 'Port can be found in settings when enabling WebUI.',
                },
                {
                    'name': 'username',
                },
                {
                    'name': 'password',
                    'type': 'password',
                },
                {
                    'name': 'label',
                    'description': 'Label to add torrent as.',
                },
                {
                    'name': 'remove_complete',
                    'label': 'Remove torrent',
                    'default': True,
                    'advanced': True,
                    'type': 'bool',
                    'description': 'Remove the torrent from uTorrent after it finished seeding.',
                },
                {
                    'name': 'delete_files',
                    'label': 'Remove files',
                    'default': True,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also remove the leftover files.',
                },
                {
                    'name': 'paused',
                    'type': 'bool',
                    'advanced': True,
                    'default': False,
                    'description': 'Add the torrent paused.',
                },
                {
                    'name': 'manual',
                    'default': 0,
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

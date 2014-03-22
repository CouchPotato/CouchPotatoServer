from base64 import b16encode, b32decode
from bencode import bencode as benc, bdecode
from couchpotato.core.downloaders.base import Downloader, ReleaseDownloadList
from couchpotato.core.helpers.encoding import isInt, ss, sp
from couchpotato.core.helpers.variable import tryInt, tryFloat, cleanHost, mergeDicts
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


## Pyload Downloader - API INFO ###
###################################
# API Documentation: http://docs.pyload.org/module/module.Api.Api.html#module.Api.Api.login
# How To Access: http://docs.pyload.org/access_api.html#using-http-json
# Examples: http://forum.pyload.org/viewtopic.php?f=7&t=2596

class pyload(Downloader):

    protocol = ['och']
    pyload_api = None
    status_flags = {
        0:      'FINISHED',
        1:      'OFFLINE',
        2:      'ONLINE',
        3:      'QUEUED',
        4:      'SKIPPED',
        5:      'WAITING',
        6:      'TEMPOFFLINE',
        7:      'STARTING',
        8:      'FAILED',
        9:      'ABORTED',
        10:     'DECRYPTING',
        11:     'CUSTOM',
        12:     'DOWNLOADING',
        13:     'PROCESSING',
        14:     'UNKNOWN'
    }

    def connect(self):
        # Load host from config and split out port.
        host = cleanHost(self.conf('host'), protocol = False).split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        self.pyload_api = pyloadAPI(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))

        return self.pyload_api

    def download(self, data = None, media = None, filedata = None):
        if not media: media = {}
        if not data: data = {}
        log.debug("Sending '%s' (%s) with url %s to pyload.", (data.get('name'), data.get('protocol'), data.get('url')))

        if not self.connect():
            return False

        och_params = {}
        if self.conf('label'):
            och_params['label'] = self.conf('label')

        if not filedata and data.get('protocol') == 'och':
            log.error('Failed sending och-Link, no data')
            return False

        py_packagename = self.createFileName(data, filedata, media)

        # Send request to pyload
        pid = 0 #package id
        if data.get('protocol') == 'och':
            pid = self.pyload_api.add_uri(py_packagename, data.get('url'), tryInt(self.conf('download_collect', default=1)))

        return self.downloadReturnId(pid)

    def test(self):
        if self.connect():
            build_version = self.pyload_api.get_build()
            if not build_version:
                return False
            if build_version < 25406:  # This build corresponds to version 3.0.0 stable
                return False, 'Your pyload client is too old, please update to newest version.'
            return True

        return False

    def getAllDownloadStatus(self, ids):

        log.debug('Checking pyload download status.')

        if not self.connect():
            return []

        release_downloads = ReleaseDownloadList(self)

        queue = self.getAllPackageIDs()

        if not queue:
            log.debug('Nothing in queue')
            return []

        # Determine Package state
        for pid in queue:
            package = self.pyload_api.get_package_data(pid)
            status = None
            files = {}
            for link in package['links']:
                if not files.has_key(link['name']):
                    files[link['name']] = []
                files[link['name']].append(link)

            finishedFiles = []
            for file in files:
                if 'FINISHED' in [self.status_flags.get(l['status']) for l in files[file]]:
                    finishedFiles.append(file)

            if len(finishedFiles) == len(files):
                status = 'finished'
            else:
                for unfinishedFile in [i for i in files if i not in finishedFiles]:
                        allFailed = True
                        for l in files[unfinishedFile]:
                            if (self.status_flags.get(l['status']) not in ['TEMPOFFLINE', 'OFFLINE', 'FAILED']) or ('captcha' in l['error']): #exclude captcha errors
                                allFailed = False
                        if allFailed:
                            status = 'failed'
                        else:
                            status = 'busy'

            release_downloads.append({
                    'id': pid,
                    'name': package['name'] if package else '',
                    'status': status if status else '',
                    #'original_status': package[''],
                    'timeleft': -1,
                    'folder': sp(package['folder']),
                    #'files': '|'.join(torrent_files)
            })

        return release_downloads

        for dl in queue:
            if dl['packageID'] in ids:

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
                elif (torrent[1] & self.status_flags['ERROR']):
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
                    'files': '|'.join(torrent_files)
                })

        return release_downloads

    def getAllPackageIDs(self):
        coll = self.pyload_api.get_Collector()
        queue = self.pyload_api.get_Queue()
        return [p['pid'] for p in (coll + queue)]

    def pause(self, release_download, pause = True):
        if not self.connect():
            return False
        return self.pyload_api.pause_torrent(release_download['id'], pause)

    def removeFailed(self, release_download):
        log.info('%s failed downloading, deleting...', release_download['name'])
        if not self.connect():
            return False
        return self.pyload_api.remove_pids([release_download['id']])

    def processComplete(self, release_download, delete_files = False):
        log.debug('Requesting uTorrent to remove the torrent %s%s.', (release_download['name'], ' and cleanup the downloaded files' if delete_files else ''))
        if not self.connect():
            return False
        return self.pyload_api.remove_torrent(release_download['id'], remove_data = delete_files)

    def removeReadOnly(self, files):
        #Removes all read-on ly flags in a for all files
        for filepath in files:
            if os.path.isfile(filepath):
                #Windows only needs S_IWRITE, but we bitwise-or with current perms to preserve other permission bits on Linux
                os.chmod(filepath, stat.S_IWRITE | os.stat(filepath).st_mode)

class pyloadAPI(object):

    def __init__(self, host = 'localhost', port = 8000, username = None, password = None):

        super(pyloadAPI, self).__init__()
        self.url = 'http://' + str(host) + ':' + str(port) + '/api/'
        self.username = username
        self.password = password
        self.sessionID = ''
        self.last_time = time.time()
        cookies = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies), MultipartPostHandler)
        self.opener.addheaders = [('User-agent', 'couchpotato-pyload-client/1.0')]
        if username and password:
            password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(realm = None, uri = self.url, user = username, passwd = password)
            self.opener.add_handler(urllib2.HTTPBasicAuthHandler(password_manager))
            self.opener.add_handler(urllib2.HTTPDigestAuthHandler(password_manager))
        elif username or password:
            log.debug('User or password missing, not using authentication.')
        self.sessionID = self.get_sessionID()

    # Logs into PyLoad and calls a various HTTP API-Request.
    #-Return: Return Message from API-Function
    def _request(self, action, data = {}):
        self.sessionID = self.get_sessionID()
        data.update({'session': self.sessionID})
        request = urllib2.Request(self.url + action, data)
        try:
            open_request = self.opener.open(request)
            response = open_request.read()
            if response:
                return response
            else:
                log.debug('Unknown failure sending command to pyload. Return text is: %s', response)
        except httplib.InvalidURL as err:
            log.error('Invalid pyLoad host, check your config %s', err)
        except urllib2.HTTPError as err:
            if err.code == 401:
                log.error('Invalid pyLoad Username or Password, check your config')
            else:
                log.error('pyLoad HTTPError: %s', err)
        except urllib2.URLError as err:
            log.error('Unable to connect to pyLoad %s', err)
        return False


## Implementation of PyLoad API FUNCTIONS ###
#############################################

    #Login into pyLoad, this must be called when using rpc before any methods can be used.
    #-Return: SessionID
    def get_sessionID(self):
        post_data = urllib.urlencode({'username': self.username, "password": self.password})
        session_request = self.opener.open(self.url + 'login', post_data)
        response = session_request.read()
        sessionID = self.sessionID
        if response != "true":
            sessionID = response
        return sessionID.replace('"', '')

    #Gets urls and returns pluginname mapped to list of matches urls.
    #-Return: {plugin: urls}
    def check_urls(self, urls):
        action = 'checkURLs'
        data = {'urls': json.dumps(urls)}
        return self._request(action, data)

    # Initiates online status check of urls
    #- Returns: online check
    def check_onlineStatus(self, url):
        action = 'checkOnlineStatus'
        data = {'urls': json.dumps(url)}
        return self._request(action, data)

    # Status off all currently running downloads.
    #- Returns: NONE
    def check_downloadStatus(self):
        action = 'statusDownloads'
        return self._request(action)

    #Adds a package, with links to desired destination.
    #- Returns:	package_id of the new package
    def add_uri(self, packagename, url, dest=1):
        action = 'addPackage'
        data = {'name': "'%s'" % packagename.encode("ascii", "ignore"),
                'links': str([url]),
                'dest': dest}
        return self._request(action, data) #packageId

    #Returns complete information about package with packageID (PID), and included files.
    #- Returns: PackageData with .links attribute
    def get_package_data(self, pid):
        action = 'getPackageData'
        data = {'pid': pid}
        try:
            return json.loads(self._request(action, data))
        except TypeError, err:
            log.debug("There's no pyLoad package with id %s" % pid)

    #Get complete information about a specific file with fileID (FID)
    #- Returns: FileData
    def get_file_data(self, fid):
        action = 'getFileData'
        data = {'fid': fid}
        try:
            return json.loads(self._request(action, data))
        except TypeError, err:
            log.debug("There's no pyLoad File with id %s" % fid)

    #Returns info about queue and packages,
    #- Returns: List of PackageInfo
    def get_Queue(self):
        action = 'getQueue'
        return json.loads(self._request(action))

    #Returns info about collector and packages,
    #- Returns: List of PackageInfo
    def get_Collector(self):
        action = 'getCollector'
        return json.loads(self._request(action))

    #Deletes packages and containing links.
    #- Returns: NONE
    def remove_pids(self, pids):
        assert isinstance(pids, list)
        action = 'deletePackages'
        data = {'pids': json.dumps(pids)}
        self._request(action, data)

    ######################################### COPIED CONTENT #########################################

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
        data = self._request('getServerVersion')
        if not data:
            return False
        return data.replace('"', '')

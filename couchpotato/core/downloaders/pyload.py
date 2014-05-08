import cookielib
import httplib
import json
import os
import re
import stat
import time
import urllib
import urllib2

from couchpotato.core._base.downloader.main import DownloaderBase, ReleaseDownloadList
from couchpotato.core.helpers.encoding import isInt, ss, sp
from couchpotato.core.helpers.variable import tryInt, cleanHost
from couchpotato.core.logger import CPLog
from libs.multipartpost import MultipartPostHandler


log = CPLog(__name__)

autoload = 'pyload'

## Pyload Downloader - API INFO ###
###################################
# API Documentation: http://docs.pyload.org/module/module.Api.Api.html#module.Api.Api.login
# How To Access: http://docs.pyload.org/access_api.html#using-http-json
# Examples: http://forum.pyload.org/viewtopic.php?f=7&t=2596

class pyload(DownloaderBase):
    time_pending = {}   #saves the time when all files finished downloading in a PID
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

        # check Connection
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
            pid = self.pyload_api.add_uri(py_packagename, json.loads(data.get('url')), tryInt(self.conf('download_collect', default=1)))
            # Cause of PID change after captcha entry:
            # Safe Package-ID (= in future CP download ID) to unused Packet-Data key 'site' to recognize release for renamer
            newName = self.pyload_api.get_package_data(pid)['name'] + '.dlID(%s)' % pid
            newData =  {'name': newName,'folder': newName}
            self.pyload_api.set_package_data(pid, newData)
            # Add Password to unrar downloaded Files
            if data.get('pwd', "") != "":
                newData = {'password': data.get('pwd')}
                self.pyload_api.set_package_data(pid, newData)
        return self.downloadReturnId(pid)

    def test(self):
        # check Connection
        if self.connect():
            build_version = self.pyload_api.get_build()
            if not build_version:
                return False
            if build_version < 25406:  # This build corresponds to version 3.0.0 stable
                return False, 'Your pyload client is too old, please update to newest version.'
            return True

        return False

    # Returms a dict that maps the DownloadID from CP with the actual PackageID in Pyload
    def getRealPID(self, ids):
        dict_id2pids = {}
        for id in ids:
            dict_id2pids[id] = []

        # check Connection
        if not self.connect():
            return []

        queue = self.getAllPackageIDs()
        if not queue:
            log.debug("No Package found in Pyload's Queue and Collector")
            return []
        for pid in queue:
            package = self.pyload_api.get_package_data(pid)
            match_dl_ID = re.search(r'dlID\((?P<id>[0-9]+)\)',package['name'])
            if match_dl_ID:
                dl_id = tryInt(match_dl_ID.group('id'), None)
                if dl_id in ids:
                    dict_id2pids[dl_id].append(pid)
                    log.debug('Found snatched release ID %s in PyLoad with Packet-ID %s.' % (dl_id, pid))
        return dict_id2pids

    #Get Download-Status from Pyload of the snatched release IDs in Couchpotato
    def getAllDownloadStatus(self, ids):

        log.debug('Checking pyload download status.')

        #get PackageIDs (PID) from PyLoad collector and queue
        queue = self.getAllPackageIDs()
        if not queue:
            log.debug('PyLoad queue is empty!')

        #list of snatched download Releases of this Downloader
        release_downloads = ReleaseDownloadList(self)

        #get a map of the actual PackageIDs in Pyload for the Download ID in CP
        map_id2pid=self.getRealPID(ids)

        # Get Package data and determine file state
        package = {}
        for dl_id in ids:
            try: # get related PIDs from pyload
                pids = map_id2pid[dl_id]
            except:
                log.debug("Can't find a Package on PyLoad of release with ID%s!", dl_id)
                pids = []
            #Ther could be more then one package of a DL-Realease ID in Pyload (two mirrors)
            pid_states = {}
            for pid in pids:
                pid_states[pid] = None
                try:
                    package = self.pyload_api.get_package_data(pid)
                    if package is None: return;

                    # Get Files in package and find Mirrors by file name.
                    files = {}
                    for link in package['links']:
                        if not files.has_key(link['name']):
                            files[link['name']] = []
                        if link['name'].split(".")[-1] != 'html': # filter wrong decrypted links
                            files[link['name']].append(link)

                    # Determine Download state from file Status (analog State_list above)

                    # - finished: all files (minimum one per mirror) have finished downloading
                    finishedFiles = []
                    for file in files:
                        if 'FINISHED' in [self.status_flags.get(l['status']) for l in files[file]]:
                            finishedFiles.append(file)

                    if len(finishedFiles) == len(files):
                        if pid in self.time_pending:
                            if (time.clock() - self.time_pending[pid]) >= self.conf('wait_time'):
                                pid_states[pid] = 'completed'
                                del self.time_pending[pid] # clean time cache of pending packages
                            else:
                                pid_states[pid] = 'pending'
                        else:
                            self.time_pending[pid] = time.clock()
                            pid_states[pid] = 'pending'
                            log.debug("Download of all files in Package %s finished. Waiting %s seconds for possible post processing in pyload.", (pid, self.conf('wait_time')))
                        break
                    # - failed: Download of a file (on all mirrors) has failed or all mirrors of a file are offline.
                    else:
                        for unfinishedFile in [i for i in files if i not in finishedFiles]:
                                allMirrorsFailed = True
                                waitForCatptcha = False
                                waitForExtracting = False
                                for l in files[unfinishedFile]:
                                    if (self.status_flags.get(l['status']) not in ['TEMPOFFLINE', 'OFFLINE', 'FAILED']):
                                        allMirrorsFailed = False
                                    if ('captcha' in l['error']):       #exclude captcha errors
                                        waitForCatptcha = True
                                    if (self.status_flags.get(l['status'])) in ['PROCESSING']: #postprocessing in pyload
                                        waitForExtracting = True

                                if allMirrorsFailed and not waitForCatptcha:
                                    log.debug('The download of all mirrors of the file %s failed or are offline. DL aborted!', l['name'])
                                    pid_states[pid] ='failed'
                                    break
                    # - unfinished: At least one file is still downloading or waiting for captcha
                                else:
                                    if waitForCatptcha:
                                        log.debug('At least one Download in Pyload is waiting for Captcha!')
                                    if waitForExtracting:
                                        log.debug('Pyload is extracting Package %s', pid)
                                    pid_states[pid] = 'busy'
                except:
                    log.debug("Can not evaluate download state of PID %s on pyLoad. Package will be removed!", pid)
                    pid_states[pid] = 'failed'

            #Determine State
            if pid_states.values().count('failed') == len(pid_states.values()):
                status = 'failed'
            elif pid_states.values().count('completed') >= 1:
                status = 'completed'
            else:
                status = 'busy'

            #directly delete all failed packages
            for pid in pid_states:
                if pid_states[pid] == 'failed':
                    self.pyload_api.remove_pids([pid])
                    if self.time_pending.has_key(pid): # clean time cache of pending packages
                        del self.time_pending[pid]

            release_downloads.append({
                    'id': dl_id,
                    'name': package['name'] if package else '',
                    'status': status if status else '',
                    'timeleft': -1,
                    'folder': sp(package['folder'])if package else '',
            })

        return release_downloads


    def getAllPackageIDs(self):
        # check Connection
        if not self.connect():
            return []

        coll = self.pyload_api.get_Collector()
        queue = self.pyload_api.get_Queue()
        return [p['pid'] for p in (coll + queue)]

    def removeFailed(self, release_download):
        log.info('%s failed downloading, deleting...', release_download['name'])
        return self.processComplete(release_download, delete_files = True)

    def processComplete(self, release_download, delete_files = False):
        log.debug('Requesting pyLoad to remove the Packet of %s%s.', (release_download['name'], ' and cleanup the downloaded files' if delete_files else ''))
        # check Connection
        if not self.connect():
            return False

        #get a map of the actual PackageID in Pyload for the Download IDs in CP
        dl_id = release_download['id']
        map_id2pid=self.getRealPID([dl_id])

        if not self.connect(): # check Connection
            return False
        elif map_id2pid[dl_id] == []:
            log.debug('No package of release with ID %s found on PyLoad. Already deleted! Nothing to do..', dl_id)
        else:
            self.pyload_api.remove_pids(map_id2pid[dl_id])
        return True

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
                'links': json.dumps(url),
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

    #Returns complete information about package with packageID (PID), and included files.
    #- Returns: PackageData with .links attribute
    def set_package_data(self, pid, data):
        action = 'setPackageData'
        data = {'pid': json.dumps(pid),
                'data': json.dumps(data)}
        try:
            json.loads(self._request(action, data))
        except TypeError, err:
            log.debug("Package data %s of PID%s could not be changed." % (data, pid))

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
        assert(isinstance(pids, list))
        action = 'deletePackages'
        data = {'pids': json.dumps(pids)}
        try:
            self._request(action, data)
        except TypeError, err:
            log.debug("Packages with PID%s could not be removed." % (data, pids))

    def get_build(self):
        data = self._request('getServerVersion')
        if not data:
            return False
        return data.replace('"', '')

config = [{
    'name': 'pyload',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'pyload',
            'label': 'pyload',
            'description': 'Use <a href="http://pyload.org/" target="_blank">pyload</a> (0.4.9+) to download files from OCH.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'OCH',
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
                    'name': 'wait_time',
                    'advanced': True,
                    'label': 'Wait Time',
                    'type': 'int',
                    'default': 90,
                    'description': 'Wait x seconds for post processing after files have finished downloading.',
                },
                {
                    'name': 'delete_files',
                    'label': 'Remove files',
                    'default': True,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Remove files when download has finished.',
                },
                {
                    'name': 'download_collect',
                    'default': 1,
                    'advanced': True,
                    'type': 'dropdown',
                    'description': 'Add snatched links to collector (manual approval necessary) or skip collector and just start downloading.',
                    'values': [('start downloading', 1), ('add to linkcollector', 0)],
                },
            ],
        }
    ],
}]
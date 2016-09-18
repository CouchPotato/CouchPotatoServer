from base64 import b16encode, b32decode, b64encode
from distutils.version import LooseVersion
from hashlib import sha1
import httplib
import json
import os
import re
import urllib2

from couchpotato.core._base.downloader.main import DownloaderBase, ReleaseDownloadList
from couchpotato.core.helpers.encoding import isInt, sp
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from bencode import bencode as benc, bdecode


log = CPLog(__name__)

autoload = 'Hadouken'


class Hadouken(DownloaderBase):
    protocol = ['torrent', 'torrent_magnet']
    hadouken_api = None

    def connect(self):
        # Load host from config and split out port.
        host = cleanHost(self.conf('host'), protocol = False).split(':')

        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        # This is where v4 and v5 begin to differ
        if(self.conf('version') == 'v4'):
            if not self.conf('api_key'):
                log.error('Config properties are not filled in correctly, API key is missing.')
                return False

            url = 'http://' + str(host[0]) + ':' + str(host[1]) + '/jsonrpc'
            client = JsonRpcClient(url, 'Token ' + self.conf('api_key'))
            self.hadouken_api = HadoukenAPIv4(client)

            return True
        else:
            auth_type = self.conf('auth_type')
            header = None

            if auth_type == 'api_key':
                header = 'Token ' + self.conf('api_key')
            elif auth_type == 'user_pass':
                header = 'Basic ' + b64encode(self.conf('auth_user') + ':' + self.conf('auth_pass'))

            url = 'http://' + str(host[0]) + ':' + str(host[1]) + '/api'
            client = JsonRpcClient(url, header)
            self.hadouken_api = HadoukenAPIv5(client)

            return True

        return False

    def download(self, data = None, media = None, filedata = None):
        """ Send a torrent/nzb file to the downloader

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

        log.debug("Sending '%s' (%s) to Hadouken.", (data.get('name'), data.get('protocol')))

        if not self.connect():
            return False

        torrent_params = {}

        if self.conf('label'):
            torrent_params['label'] = self.conf('label')
            # Set the tags array since that is what v5 expects.
            torrent_params['tags'] = [self.conf('label')]

        torrent_filename = self.createFileName(data, filedata, media)

        if data.get('protocol') == 'torrent_magnet':
            torrent_hash = re.findall('urn:btih:([\w]{32,40})', data.get('url'))[0].upper()
            torrent_params['trackers'] = self.torrent_trackers
            torrent_params['name'] = torrent_filename
        else:
            info = bdecode(filedata)['info']
            torrent_hash = sha1(benc(info)).hexdigest().upper()

        # Convert base 32 to hex
        if len(torrent_hash) == 32:
            torrent_hash = b16encode(b32decode(torrent_hash))

        # Send request to Hadouken
        if data.get('protocol') == 'torrent_magnet':
            self.hadouken_api.add_magnet_link(data.get('url'), torrent_params)
        else:
            self.hadouken_api.add_file(filedata, torrent_params)

        return self.downloadReturnId(torrent_hash)

    def test(self):
        """ Tests the given host:port and API key """

        if not self.connect():
            return False

        version = self.hadouken_api.get_version()

        if not version:
            log.error('Could not get Hadouken version.')
            return False

        # The minimum required version of Hadouken is 4.5.6.
        if LooseVersion(version) >= LooseVersion('4.5.6'):
            return True

        log.error('Hadouken v4.5.6 (or newer) required. Found v%s', version)
        return False

    def getAllDownloadStatus(self, ids):
        """ Get status of all active downloads

        :param ids: list of (mixed) downloader ids
            Used to match the releases for this downloader as there could be
            other downloaders active that it should ignore
        :return: list of releases
        """

        log.debug('Checking Hadouken download status.')

        if not self.connect():
            return []

        release_downloads = ReleaseDownloadList(self)
        queue = self.hadouken_api.get_by_hash_list(ids)

        if not queue:
            return []

        for torrent in queue:
            if torrent is None:
                continue

            torrent_filelist = self.hadouken_api.get_files_by_hash(torrent.info_hash)
            torrent_files = []

            for file_item in torrent_filelist:
                torrent_files.append(sp(os.path.join(torrent.save_path, file_item)))

            release_downloads.append({
                'id': torrent.info_hash.upper(),
                'name': torrent.name,
                'status': torrent.get_status(),
                'seed_ratio': torrent.get_seed_ratio(),
                'original_status': torrent.state,
                'timeleft': -1,
                'folder': sp(torrent.save_path if len(torrent_files == 1) else os.path.join(torrent.save_path, torrent.name)),
                'files': torrent_files
            })

        return release_downloads

    def pause(self, release_download, pause = True):
        """ Pauses or resumes the torrent specified by the ID field
        in release_download.

        Keyword arguments:
        release_download -- The CouchPotato release_download to pause/resume.
        pause -- Boolean indicating whether to pause or resume.
        """

        if not self.connect():
            return False

        return self.hadouken_api.pause(release_download['id'], pause)

    def removeFailed(self, release_download):
        """ Removes a failed torrent and also remove the data associated with it.

        Keyword arguments:
        release_download -- The CouchPotato release_download to remove.
        """

        log.info('%s failed downloading, deleting...', release_download['name'])

        if not self.connect():
            return False

        return self.hadouken_api.remove(release_download['id'], remove_data = True)

    def processComplete(self, release_download, delete_files = False):
        """ Removes the completed torrent from Hadouken and optionally removes the data
        associated with it.

        Keyword arguments:
        release_download -- The CouchPotato release_download to remove.
        delete_files: Boolean indicating whether to remove the associated data.
        """

        log.debug('Requesting Hadouken to remove the torrent %s%s.',
                  (release_download['name'], ' and cleanup the downloaded files' if delete_files else ''))

        if not self.connect():
            return False

        return self.hadouken_api.remove(release_download['id'], remove_data = delete_files)


class JsonRpcClient(object):
    def __init__(self, url, auth_header = None):
        self.url = url
        self.requestId = 0

        self.opener = urllib2.build_opener()
        self.opener.addheaders = [
            ('User-Agent', 'couchpotato-hadouken-client/1.0'),
            ('Accept', 'application/json'),
            ('Content-Type', 'application/json')
        ]

        if auth_header:
            self.opener.addheaders.append(('Authorization', auth_header))

    def invoke(self, method, params):
        self.requestId += 1

        data = {
            'jsonrpc': '2.0',
            'id': self.requestId,
            'method': method,
            'params': params
        }

        request = urllib2.Request(self.url, data = json.dumps(data))

        try:
            f = self.opener.open(request)
            response = f.read()
            f.close()

            obj = json.loads(response)

            if 'error' in obj.keys():
                log.error('JSONRPC error, %s: %s', (obj['error']['code'], obj['error']['message']))
                return False

            if 'result' in obj.keys():
                return obj['result']

            return True
        except httplib.InvalidURL as err:
            log.error('Invalid Hadouken host, check your config %s', err)
        except urllib2.HTTPError as err:
            if err.code == 401:
                log.error('Could not authenticate, check your config')
            else:
                log.error('Hadouken HTTPError: %s', err)
        except urllib2.URLError as err:
            log.error('Unable to connect to Hadouken %s', err)

        return False


class HadoukenAPI(object):
    def __init__(self, rpc_client):
        self.rpc = rpc_client

        if not rpc_client:
            log.error('No JSONRPC client specified.')

    def add_file(self, data, params):
        """ Add a file to Hadouken with the specified parameters.

        Keyword arguments:
        filedata -- The binary torrent data.
        torrent_params -- Additional parameters for the file.
        """
        pass

    def add_magnet_link(self, link, params):
        """ Add a magnet link to Hadouken with the specified parameters.

        Keyword arguments:
        magnetLink -- The magnet link to send.
        torrent_params -- Additional parameters for the magnet link.
        """
        pass

    def get_by_hash_list(self, infoHashList):
        """ Gets a list of torrents filtered by the given info hash list.

        Keyword arguments:
        infoHashList -- A list of info hashes.
        """
        pass

    def get_files_by_hash(self, infoHash):
        """ Gets a list of files for the torrent identified by the
        given info hash.

        Keyword arguments:
        infoHash -- The info hash of the torrent to return files for.
        """
        pass

    def get_version(self):
        """ Gets the version, commitish and build date of Hadouken. """
        pass

    def pause(self, infoHash, pause):
        """ Pauses/unpauses the torrent identified by the given info hash.

        Keyword arguments:
        infoHash -- The info hash of the torrent to operate on.
        pause -- If true, pauses the torrent. Otherwise resumes.
        """
        pass

    def remove(self, infoHash, remove_data = False):
        """ Removes the torrent identified by the given info hash and
        optionally removes the data as well.

        Keyword arguments:
        infoHash -- The info hash of the torrent to remove.
        remove_data -- If true, removes the data associated with the torrent.
        """
        pass


class TorrentItem(object):
    @property
    def info_hash(self):
        pass

    @property
    def save_path(self):
        pass

    @property
    def name(self):
        pass

    @property
    def state(self):
        pass

    def get_status(self):
        """ Returns the CouchPotato status for a given torrent."""
        pass

    def get_seed_ratio(self):
        """ Returns the seed ratio for a given torrent."""
        pass


class TorrentItemv5(TorrentItem):
    def __init__(self, obj):
        self.obj = obj

    def info_hash(self):
        return self.obj[0]

    def save_path(self):
        return self.obj[26]

    def name(self):
        return self.obj[2]

    def state(self):
        return self.obj[1]

    def get_status(self):
        if self.obj[1] == 32:
            return 'completed'

        if self.obj[1] == 1:
            return 'seeding'

        return 'busy'

    def get_seed_ratio(self):
        up   = self.obj[6]
        down = self.obj[5]

        if up > 0 and down > 0:
            return up / down

        return 0


class HadoukenAPIv5(HadoukenAPI):

    def add_file(self, data, params):
        return self.rpc.invoke('webui.addTorrent', ['file', b64encode(data), params])

    def add_magnet_link(self, link, params):
        return self.rpc.invoke('webui.addTorrent', ['url', link, params])

    def get_by_hash_list(self, infoHashList):
        torrents = self.rpc.invoke('webui.list', None)
        result = []

        for torrent in torrents['torrents']:
            if torrent[0] in infoHashList:
                result.append(TorrentItemv5(torrent))

        return result

    def get_files_by_hash(self, infoHash):
        files = self.rpc.invoke('webui.getFiles', [infoHash])
        result = []

        for file in files['files'][1]:
            result.append(file[0])

        return result

    def get_version(self):
        result = self.rpc.invoke('core.getSystemInfo', None)

        if not result:
            return False

        return result['versions']['hadouken']

    def pause(self, infoHash, pause):
        if pause:
            return self.rpc.invoke('webui.perform', ['pause', infoHash])

        return self.rpc.invoke('webui.perform', ['resume', infoHash])

    def remove(self, infoHash, remove_data=False):
        if remove_data:
            return self.rpc.invoke('webui.perform', ['removedata', infoHash])

        return self.rpc.invoke('webui.perform', ['remove', infoHash])


class TorrentItemv4(TorrentItem):
    def __init__(self, obj):
        self.obj = obj

    def info_hash(self):
        return self.obj['InfoHash']

    def save_path(self):
        return self.obj['SavePath']

    def name(self):
        return self.obj['Name']

    def state(self):
        return self.obj['State']

    def get_status(self):
        if self.obj['IsSeeding'] and self.obj['IsFinished'] and self.obj['Paused']:
            return 'completed'

        if self.obj['IsSeeding']:
            return 'seeding'

        return 'busy'

    def get_seed_ratio(self):
        up   = self.obj['TotalUploadedBytes']
        down = self.obj['TotalDownloadedBytes']

        if up > 0 and down > 0:
            return up / down

        return 0


class HadoukenAPIv4(object):
    def add_file(self, data, params):
        return self.rpc.invoke('torrents.addFile', [b64encode(data), params])

    def add_magnet_link(self, link, params):
        return self.rpc.invoke('torrents.addUrl', [link, params])

    def get_by_hash_list(self, infoHashList):
        torrents = self.rpc.invoke('torrents.getByInfoHashList', [infoHashList])
        result = []

        for torrent in torrents:
            result.append(TorrentItemv4(torrent))

        return result

    def get_files_by_hash(self, infoHash):
        files = self.rpc.invoke('torrents.getFiles', [infoHash])
        result = []

        for file in files:
            result.append(file['Path'])

        return result

    def get_version(self):
        result = self.rpc.invoke('core.getVersion', None)

        if not result:
            return False

        return result['Version']

    def pause(self, infoHash, pause):
        if pause:
            return self.rpc.invoke('torrents.pause', [infoHash])

        return self.rpc.invoke('torrents.resume', [infoHash])

    def remove(self, infoHash, remove_data = False):
        return self.rpc.invoke('torrents.remove', [infoHash, remove_data])


config = [{
    'name': 'hadouken',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'hadouken',
            'label': 'Hadouken',
            'description': 'Use <a href="http://www.hdkn.net" target="_blank">Hadouken</a> (>= v4.5.6) to download torrents.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'torrent'
                },
                {
                    'name': 'version',
                    'label': 'Version',
                    'type': 'dropdown',
                    'default': 'v4',
                    'values': [('v4.x', 'v4'), ('v5.x', 'v5')],
                    'description': 'Hadouken version.',
                },
                {
                    'name': 'host',
                    'default': 'localhost:7890'
                },
                {
                    'name': 'auth_type',
                    'label': 'Auth. type',
                    'type': 'dropdown',
                    'default': 'api_key',
                    'values': [('None', 'none'), ('API key/Token', 'api_key'), ('Username/Password', 'user_pass')],
                    'description': 'Type of authentication',
                },
                {
                    'name': 'api_key',
                    'label': 'API key (v4)/Token (v5)',
                    'type': 'password'
                },
                {
                    'name': 'auth_user',
                    'label': 'Username',
                    'description': '(only for v5)'
                },
                {
                    'name': 'auth_pass',
                    'label': 'Password',
                    'type': 'password',
                    'description': '(only for v5)'
                },
                {
                    'name': 'label',
                    'description': 'Label to add torrent as.'
                }
            ]
        }
    ]
}]

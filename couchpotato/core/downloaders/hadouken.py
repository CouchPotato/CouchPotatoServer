from couchpotato.core._base.downloader.main import DownloaderBase, ReleaseDownloadList
from couchpotato.core.helpers.encoding import isInt, ss, sp
from couchpotato.core.helpers.variable import tryInt, tryFloat, cleanHost
from couchpotato.core.logger import CPLog

from base64 import b16encode, b32decode, b64encode
from distutils.version import LooseVersion
import httplib
import json
import os
import re
import urllib
import urllib2

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

        if not self.conf('apikey'):
            log.error('Config properties are not filled in correctly, API key is missing.')
            return False

        self.hadouken_api = HadoukenAPI(host[0], port = host[1], apiKey = self.conf('apikey'))

        return True

    def download(self, data = None, media = None, filedata = None):
        if not media: media = {}
        if not data: data = {}

        log.debug("Sending '%s' (%s) to Hadouken.", (data.get('name'), data.get('protocol')))

        if not self.connect():
            return False

        torrent_params = {}

        if self.conf('label'):
            torrent_params['label'] = self.conf('label')

        torrent_filename = self.createFileName(data, filedata, media)

        if data.get('protocol') == 'torrent_magnet':
            torrent_hash = re.findall('urn:btih:([\w]{32,40})', data.get('url'))[0].upper()
            torrent_params['trackers'] = self.torrent_trackers
            torrent_params['name'] = torrent_filename
        else:
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

        if LooseVersion(version) >= LooseVersion('4.4.1'):
            return True

        log.error('Hadouken v4.1.1 (or newer) required. Found v%s', version)
        return False

    def getAllDownloadStatus(self, ids):
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

            torrent_dir = os.path.join(torrent['SavePath'], torrent['Name'])
            torrent_files = []
            status = 'busy'

            for torrent_file in torrent['Files']:
                torrent_files.append(sp(os.path.join(torrent['SavePath'], torrent_file['Path'])))

            if os.path.isdir(torrent_dir):
                torrent['SavePath'] = torrent_dir

            release_downloads.append({
                'id': torrent['InfoHash'].upper(),
                'name': torrent['Name'],
                'status': self.get_torrent_status(torrent),
                'seed_ratio': self.get_seed_ratio(torrent),
                'original_status': torrent['State'],
                'timeleft': -1,
                'folder': sp(torrent['SavePath']),
                'files': torrent_files
            })

        return release_downloads

    def get_seed_ratio(self, torrent):
        """ Returns the seed ratio for a given torrent.

        Keyword arguments:
        torrent -- The torrent to calculate seed ratio for.
        """

        up = torrent['TotalUploadedBytes']
        down = torrent['TotalDownloadedBytes']

        if up > 0 and down > 0:
            return up / down

        return 0

    def get_torrent_status(self, torrent):
        """ Returns the CouchPotato status for a given torrent.

        Keyword arguments:
        torrent -- The torrent to translate status for.
        """

        if torrent['IsSeeding'] and torrent['IsFinished'] and torrent['Paused']:
            return 'completed'

        if torrent['IsSeeding']:
            return 'seeding'

        return 'busy'

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

        log.debug('Requesting Hadouken to remove the torrent %s%s.', (release_download['name'], ' and cleanup the downloaded files' if delete_files else ''))

        if not self.connect():
            return False

        return self.hadouken_api.remove(release_download['id'], remove_data = delete_files)

class HadoukenAPI(object):
    def __init__(self, host = 'localhost', port = 7890, apiKey = None):
        self.url = 'http://' + str(host) + ':' + str(port)
        self.apiKey = apiKey
        self.requestId = 0;

        self.opener = urllib2.build_opener()
        self.opener.addheaders = [('User-agent', 'couchpotato-hadouken-client/1.0'), ('Accept', 'application/json')]

        if not apiKey:
            log.error('API key missing.')

    def add_file(self, filedata, torrent_params):
        data = {
            'method': 'torrents.addFile',
            'params': [ b64encode(filedata), torrent_params ]
        }

        return self._request('/jsonrpc', data)

    def add_magnet_link(self, magnetLink, torrent_params):
        data = {
            'method': 'torrents.addUrl',
            'params': [ magnetLink, torrent_params ]
        }

        return self._request('/jsonrpc', data)

    def get_by_hash_list(self, infoHashList):
        data = {
            'method': 'torrents.getByInfoHashList',
            'params': [ infoHashList ]
        }

        return self._request('/jsonrpc', data)

    def get_version(self):
        data = {
            'method': 'core.getVersion',
            'params': None
        }

        result = self._request('/jsonrpc', data)

        if not result:
            return False

        return result['Version']

    def pause(self, id, pause):
        data = {
            'method': 'torrents.pause',
            'params': [ id ]
        }

        if not pause:
            data['method'] = 'torrents.resume'

        return self._request('/jsonrpc', data)

    def remove(self, id, remove_data = False):
        data = {
            'method': 'torrents.remove',
            'params': [ id, remove_data ]
        }

        return self._request('/jsonrpc', data)


    def _request(self, url, data):
        self.requestId += 1

        data['jsonrpc'] = '2.0'
        data['id'] = self.requestId

        request = urllib2.Request(self.url + url, data = json.dumps(data))
        request.add_header('Authorization', 'Token ' + self.apiKey)
        request.add_header('Content-Type', 'application/json')

        try:
            f = self.opener.open(request)
            response = f.read()
            f.close()

            obj = json.loads(response)

            if not 'error' in obj.keys():
                return obj['result']

            log.error('JSONRPC error, %s: %s', obj['error']['code'], obj['error']['message'])
        except httplib.InvalidURL as err:
            log.error('Invalid Hadouken host, check your config %s', err)
        except urllib2.HTTPError as err:
            if err.code == 401:
                log.error('Invalid Hadouken API key, check your config')
            else:
                log.error('Hadouken HTTPError: %s', err)
        except urllib2.URLError as err:
            log.error('Unable to connect to Hadouken %s', err)
        
        return False
        

config = [{
    'name': 'hadouken',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'hadouken',
            'label': 'Hadouken',
            'description': 'Use <a href="http://www.hdkn.net">Hadouken</a> (>= v4.4.1) to download torrents.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'torrent'
                },
                {
                    'name': 'host',
                    'default': 'localhost:7890'
                },
                {
                    'name': 'apikey',
                    'label': 'API key',
                    'type': 'password'
                }
            ]
        }
    ]
}]
from base64 import b64encode
from couchpotato.core.downloaders.base import Downloader, ReleaseDownloadList
from couchpotato.core.helpers.encoding import isInt, ss
from couchpotato.core.helpers.variable import tryInt, tryFloat
from couchpotato.core.logger import CPLog
from datetime import timedelta
import httplib
import json
import os.path
import re
import urllib2

log = CPLog(__name__)


class Transmission(Downloader):

    protocol = ['torrent', 'torrent_magnet']
    log = CPLog(__name__)
    trpc = None

    def connect(self):
        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        if not self.trpc:
            self.trpc = TransmissionRPC(host[0], port = host[1], rpc_url = self.conf('rpc_url'), username = self.conf('username'), password = self.conf('password'))

        return self.trpc

    def download(self, data, movie, filedata = None):

        log.info('Sending "%s" (%s) to Transmission.', (data.get('name'), data.get('protocol')))

        if not self.connect():
            return False

        if not filedata and data.get('protocol') == 'torrent':
            log.error('Failed sending torrent, no data')
            return False

        # Set parameters for adding torrent
        params = {
            'paused': self.conf('paused', default = False)
        }

        if self.conf('directory'):
            if os.path.isdir(self.conf('directory')):
                params['download-dir'] = self.conf('directory')
            else:
                log.error('Download directory from Transmission settings: %s doesn\'t exist', self.conf('directory'))

        # Change parameters of torrent
        torrent_params = {}
        if data.get('seed_ratio'):
            torrent_params['seedRatioLimit'] = tryFloat(data.get('seed_ratio'))
            torrent_params['seedRatioMode'] = 1

        if data.get('seed_time'):
            torrent_params['seedIdleLimit'] = tryInt(data.get('seed_time')) * 60
            torrent_params['seedIdleMode'] = 1

        # Send request to Transmission
        if data.get('protocol') == 'torrent_magnet':
            remote_torrent = self.trpc.add_torrent_uri(data.get('url'), arguments = params)
            torrent_params['trackerAdd'] = self.torrent_trackers
        else:
            remote_torrent = self.trpc.add_torrent_file(b64encode(filedata), arguments = params)

        if not remote_torrent:
            log.error('Failed sending torrent to Transmission')
            return False

        # Change settings of added torrents
        if torrent_params:
            self.trpc.set_torrent(remote_torrent['torrent-added']['hashString'], torrent_params)

        log.info('Torrent sent to Transmission successfully.')
        return self.downloadReturnId(remote_torrent['torrent-added']['hashString'])

    def getAllDownloadStatus(self):

        log.debug('Checking Transmission download status.')

        if not self.connect():
            return False

        release_downloads = ReleaseDownloadList(self)

        return_params = {
            'fields': ['id', 'name', 'hashString', 'percentDone', 'status', 'eta', 'isStalled', 'isFinished', 'downloadDir', 'uploadRatio', 'secondsSeeding', 'seedIdleLimit', 'files']
        }

        queue = self.trpc.get_alltorrents(return_params)
        if not (queue and queue.get('torrents')):
            log.debug('Nothing in queue or error')
            return False

        for torrent in queue['torrents']:
            log.debug('name=%s / id=%s / downloadDir=%s / hashString=%s / percentDone=%s / status=%s / eta=%s / uploadRatio=%s / isFinished=%s',
                (torrent['name'], torrent['id'], torrent['downloadDir'], torrent['hashString'], torrent['percentDone'], torrent['status'], torrent['eta'], torrent['uploadRatio'], torrent['isFinished']))

            torrent_files = []
            for file_item in torrent['files']:
                torrent_files.append(os.path.normpath(os.path.join(ss(torrent['downloadDir']), ss(file_item['name']))))

            status = 'busy'
            if torrent['isStalled'] and self.conf('stalled_as_failed'):
                status = 'failed'
            elif torrent['status'] == 0 and torrent['percentDone'] == 1:
                status = 'completed'
            elif torrent['status'] in [5, 6]:
                status = 'seeding'

            release_downloads.append({
                'id': torrent['hashString'],
                'name': torrent['name'],
                'status': status,
                'original_status': torrent['status'],
                'seed_ratio': torrent['uploadRatio'],
                'timeleft': str(timedelta(seconds = torrent['eta'])),
                'folder': os.path.normpath(ss(torrent['downloadDir'])) if len(torrent_files) == 1 else os.path.normpath(os.path.join(ss(torrent['downloadDir']), ss(torrent['name']))),
                'files': ss('|'.join(torrent_files))
            })

        return release_downloads

    def pause(self, release_download, pause = True):
        if pause:
            return self.trpc.stop_torrent(release_download['id'])
        else:
            return self.trpc.start_torrent(release_download['id'])

    def removeFailed(self, release_download):
        log.info('%s failed downloading, deleting...', release_download['name'])
        return self.trpc.remove_torrent(release_download['id'], True)

    def processComplete(self, release_download, delete_files = False):
        log.debug('Requesting Transmission to remove the torrent %s%s.', (release_download['name'], ' and cleanup the downloaded files' if delete_files else ''))
        return self.trpc.remove_torrent(release_download['id'], delete_files)

class TransmissionRPC(object):

    """TransmissionRPC lite library"""
    def __init__(self, host = 'localhost', port = 9091, rpc_url = 'transmission', username = None, password = None):

        super(TransmissionRPC, self).__init__()

        self.url = 'http://' + host + ':' + str(port) + '/' + rpc_url + '/rpc'
        self.tag = 0
        self.session_id = 0
        self.session = {}
        if username and password:
            password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(realm = None, uri = self.url, user = username, passwd = password)
            opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(password_manager), urllib2.HTTPDigestAuthHandler(password_manager))
            opener.addheaders = [('User-agent', 'couchpotato-transmission-client/1.0')]
            urllib2.install_opener(opener)
        elif username or password:
            log.debug('User or password missing, not using authentication.')
        self.session = self.get_session()

    def _request(self, ojson):
        self.tag += 1
        headers = {'x-transmission-session-id': str(self.session_id)}
        request = urllib2.Request(self.url, json.dumps(ojson).encode('utf-8'), headers)
        try:
            open_request = urllib2.urlopen(request)
            response = json.loads(open_request.read())
            log.debug('request: %s', json.dumps(ojson))
            log.debug('response: %s', json.dumps(response))
            if response['result'] == 'success':
                log.debug('Transmission action successful')
                return response['arguments']
            else:
                log.debug('Unknown failure sending command to Transmission. Return text is: %s', response['result'])
                return False
        except httplib.InvalidURL, err:
            log.error('Invalid Transmission host, check your config %s', err)
            return False
        except urllib2.HTTPError, err:
            if err.code == 401:
                log.error('Invalid Transmission Username or Password, check your config')
                return False
            elif err.code == 409:
                msg = str(err.read())
                try:
                    self.session_id = \
                        re.search('X-Transmission-Session-Id:\s*(\w+)', msg).group(1)
                    log.debug('X-Transmission-Session-Id: %s', self.session_id)

                    # #resend request with the updated header

                    return self._request(ojson)
                except:
                    log.error('Unable to get Transmission Session-Id %s', err)
            else:
                log.error('TransmissionRPC HTTPError: %s', err)
        except urllib2.URLError, err:
            log.error('Unable to connect to Transmission %s', err)

    def get_session(self):
        post_data = {'method': 'session-get', 'tag': self.tag}
        return self._request(post_data)

    def add_torrent_uri(self, torrent, arguments):
        arguments['filename'] = torrent
        post_data = {'arguments': arguments, 'method': 'torrent-add', 'tag': self.tag}
        return self._request(post_data)

    def add_torrent_file(self, torrent, arguments):
        arguments['metainfo'] = torrent
        post_data = {'arguments': arguments, 'method': 'torrent-add', 'tag': self.tag}
        return self._request(post_data)

    def set_torrent(self, torrent_id, arguments):
        arguments['ids'] = torrent_id
        post_data = {'arguments': arguments, 'method': 'torrent-set', 'tag': self.tag}
        return self._request(post_data)

    def get_alltorrents(self, arguments):
        post_data = {'arguments': arguments, 'method': 'torrent-get', 'tag': self.tag}
        return self._request(post_data)

    def stop_torrent(self, torrent_id):
        post_data = {'arguments': {'ids': torrent_id}, 'method': 'torrent-stop', 'tag': self.tag}
        return self._request(post_data)

    def start_torrent(self, torrent_id):
        post_data = {'arguments': {'ids': torrent_id}, 'method': 'torrent-start', 'tag': self.tag}
        return self._request(post_data)

    def remove_torrent(self, torrent_id, delete_local_data):
        post_data = {'arguments': {'ids': torrent_id, 'delete-local-data': delete_local_data}, 'method': 'torrent-remove', 'tag': self.tag}
        return self._request(post_data)


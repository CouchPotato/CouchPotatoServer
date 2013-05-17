from base64 import b64encode
from couchpotato.core.downloaders.base import Downloader, StatusList
from couchpotato.core.helpers.encoding import isInt
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
from datetime import timedelta
import httplib
import json
import os.path
import re
import traceback
import urllib2

log = CPLog(__name__)


class Transmission(Downloader):

    type = ['torrent', 'torrent_magnet']
    log = CPLog(__name__)

    def download(self, data, movie, filedata = None):

        log.info('Sending "%s" (%s) to Transmission.', (data.get('name'), data.get('type')))

        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        # Set parameters for Transmission
        params = {
            'paused': self.conf('paused', default = 0),
        }

        if len(self.conf('directory', default = '')) > 0:
            folder_name = self.createFileName(data, filedata, movie)[:-len(data.get('type')) - 1]
            folder_path = os.path.join(self.conf('directory', default = ''), folder_name).rstrip(os.path.sep)

            # Create the empty folder to download too
            self.makeDir(folder_path)

            params['download-dir'] = folder_path

        torrent_params = {}
        if self.conf('ratio'):
            torrent_params = {
                'seedRatioLimit': self.conf('ratio'),
                'seedRatioMode': self.conf('ratiomode')
            }

        if not filedata and data.get('type') == 'torrent':
            log.error('Failed sending torrent, no data')
            return False

        # Send request to Transmission
        try:
            trpc = TransmissionRPC(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))
            if data.get('type') == 'torrent_magnet':
                remote_torrent = trpc.add_torrent_uri(data.get('url'), arguments = params)
                torrent_params['trackerAdd'] = self.torrent_trackers
            else:
                remote_torrent = trpc.add_torrent_file(b64encode(filedata), arguments = params)

            if not remote_torrent:
                return False

            # Change settings of added torrents
            elif torrent_params:
                trpc.set_torrent(remote_torrent['torrent-added']['hashString'], torrent_params)

            log.info('Torrent sent to Transmission successfully.')
            return self.downloadReturnId(remote_torrent['torrent-added']['hashString'])
        except:
            log.error('Failed to change settings for transfer: %s', traceback.format_exc())
            return False

    def getAllDownloadStatus(self):

        log.debug('Checking Transmission download status.')

        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        # Go through Queue
        try:
            trpc = TransmissionRPC(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))
            return_params = {
                'fields': ['id', 'name', 'hashString', 'percentDone', 'status', 'eta', 'isFinished', 'downloadDir', 'uploadRatio']
            }
            queue = trpc.get_alltorrents(return_params)

        except Exception, err:
            log.error('Failed getting queue: %s', err)
            return False

        statuses = StatusList(self)

        # Get torrents status
            # CouchPotato Status
                #status = 'busy'
                #status = 'failed'
                #status = 'completed'
            # Transmission Status
                #status = 0 => "Torrent is stopped"
                #status = 1 => "Queued to check files"
                #status = 2 => "Checking files"
                #status = 3 => "Queued to download"
                #status = 4 => "Downloading"
                #status = 4 => "Queued to seed"
                #status = 6 => "Seeding"
        #To do :
        #   add checking file
        #   manage no peer in a range time => fail

        for item in queue['torrents']:
            log.debug('name=%s / id=%s / downloadDir=%s / hashString=%s / percentDone=%s / status=%s / eta=%s / uploadRatio=%s / confRatio=%s / isFinished=%s', (item['name'], item['id'], item['downloadDir'], item['hashString'], item['percentDone'], item['status'], item['eta'], item['uploadRatio'], self.conf('ratio'), item['isFinished']))

            if not os.path.isdir(Env.setting('from', 'renamer')):
                log.error('Renamer "from" folder doesn\'t to exist.')
                return

            if (item['percentDone'] * 100) >= 100 and (item['status'] == 6 or item['status'] == 0) and item['uploadRatio'] > self.conf('ratio'):
                try:
                    trpc.stop_torrent(item['hashString'], {})
                    statuses.append({
                        'id': item['hashString'],
                        'name': item['name'],
                        'status': 'completed',
                        'original_status': item['status'],
                        'timeleft': str(timedelta(seconds = 0)),
                        'folder': os.path.join(item['downloadDir'], item['name']),
                    })
                except Exception, err:
                    log.error('Failed to stop and remove torrent "%s" with error: %s', (item['name'], err))
                    statuses.append({
                        'id': item['hashString'],
                        'name': item['name'],
                        'status': 'failed',
                        'original_status': item['status'],
                        'timeleft': str(timedelta(seconds = 0)),
                    })
            else:
                statuses.append({
                    'id': item['hashString'],
                    'name': item['name'],
                    'status': 'busy',
                    'original_status': item['status'],
                    'timeleft': str(timedelta(seconds = item['eta'])), # Is ETA in seconds??
                })

        return statuses

class TransmissionRPC(object):

    """TransmissionRPC lite library"""

    def __init__(self, host = 'localhost', port = 9091, username = None, password = None):

        super(TransmissionRPC, self).__init__()

        self.url = 'http://' + host + ':' + str(port) + '/transmission/rpc'
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
                log.debug('Transmission action successfull')
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

    def stop_torrent(self, torrent_id, arguments):
        arguments['ids'] = torrent_id
        post_data = {'arguments': arguments, 'method': 'torrent-stop', 'tag': self.tag}
        return self._request(post_data)

    def remove_torrent(self, torrent_id, remove_local_data, arguments):
        arguments['ids'] = torrent_id
        arguments['delete-local-data'] = remove_local_data
        post_data = {'arguments': arguments, 'method': 'torrent-remove', 'tag': self.tag}
        return self._request(post_data)

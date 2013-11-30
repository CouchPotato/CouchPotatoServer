from base64 import b64encode, b16encode, b32decode
from bencode import bencode as benc, bdecode
from couchpotato.core.downloaders.base import Downloader, ReleaseDownloadList
from couchpotato.core.helpers.encoding import isInt, sp
from couchpotato.core.helpers.variable import tryFloat
from couchpotato.core.logger import CPLog
from datetime import timedelta
from hashlib import sha1
from synchronousdeluge import DelugeClient
import os.path
import re
import traceback

log = CPLog(__name__)


class Deluge(Downloader):

    protocol = ['torrent', 'torrent_magnet']
    log = CPLog(__name__)
    drpc = None

    def connect(self):
        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        if not self.drpc:
            self.drpc = DelugeRPC(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))

        return self.drpc

    def download(self, data = None, media = None, filedata = None):
        if not media: media = {}
        if not data: data = {}

        log.info('Sending "%s" (%s) to Deluge.', (data.get('name'), data.get('protocol')))

        if not self.connect():
            return False

        if not filedata and data.get('protocol') == 'torrent':
            log.error('Failed sending torrent, no data')
            return False

        # Set parameters for Deluge
        options = {
            'add_paused': self.conf('paused', default = 0),
            'label': self.conf('label')
        }

        if self.conf('directory'):
            if os.path.isdir(self.conf('directory')):
                options['download_location'] = self.conf('directory')
            else:
                log.error('Download directory from Deluge settings: %s doesn\'t exist', self.conf('directory'))

        if self.conf('completed_directory'):
            if os.path.isdir(self.conf('completed_directory')):
                options['move_completed'] = 1
                options['move_completed_path'] = self.conf('completed_directory')
            else:
                log.error('Download directory from Deluge settings: %s doesn\'t exist', self.conf('directory'))

        if data.get('seed_ratio'):
            options['stop_at_ratio'] = 1
            options['stop_ratio'] = tryFloat(data.get('seed_ratio'))

#        Deluge only has seed time as a global option. Might be added in
#        in a future API release.
#        if data.get('seed_time'):

        # Send request to Deluge
        if data.get('protocol') == 'torrent_magnet':
            remote_torrent = self.drpc.add_torrent_magnet(data.get('url'), options)
        else:
            filename = self.createFileName(data, filedata, media)
            remote_torrent = self.drpc.add_torrent_file(filename, filedata, options)

        if not remote_torrent:
            log.error('Failed sending torrent to Deluge')
            return False

        log.info('Torrent sent to Deluge successfully.')
        return self.downloadReturnId(remote_torrent)

    def getAllDownloadStatus(self):

        log.debug('Checking Deluge download status.')

        if not self.connect():
            return False

        release_downloads = ReleaseDownloadList(self)

        queue = self.drpc.get_alltorrents()

        if not queue:
            log.debug('Nothing in queue or error')
            return False

        for torrent_id in queue:
            torrent = queue[torrent_id]
            log.debug('name=%s / id=%s / save_path=%s / move_completed_path=%s / hash=%s / progress=%s / state=%s / eta=%s / ratio=%s / stop_ratio=%s / is_seed=%s / is_finished=%s / paused=%s', (torrent['name'], torrent['hash'], torrent['save_path'], torrent['move_completed_path'], torrent['hash'], torrent['progress'], torrent['state'], torrent['eta'], torrent['ratio'], torrent['stop_ratio'], torrent['is_seed'], torrent['is_finished'], torrent['paused']))

            # Deluge has no easy way to work out if a torrent is stalled or failing.
            #status = 'failed'
            status = 'busy'
            if torrent['is_seed'] and tryFloat(torrent['ratio']) < tryFloat(torrent['stop_ratio']):
                # We have torrent['seeding_time'] to work out what the seeding time is, but we do not
                # have access to the downloader seed_time, as with deluge we have no way to pass it
                # when the torrent is added. So Deluge will only look at the ratio.
                # See above comment in download().
                status = 'seeding'
            elif torrent['is_seed'] and torrent['is_finished'] and torrent['paused'] and torrent['state'] == 'Paused':
                status = 'completed'

            download_dir = sp(torrent['save_path'])
            if torrent['move_on_completed']:
                download_dir = torrent['move_completed_path']

            torrent_files = []
            for file_item in torrent['files']:
                torrent_files.append(sp(os.path.join(download_dir, file_item['path'])))

            release_downloads.append({
                'id': torrent['hash'],
                'name': torrent['name'],
                'status': status,
                'original_status': torrent['state'],
                'seed_ratio': torrent['ratio'],
                'timeleft': str(timedelta(seconds = torrent['eta'])),
                'folder': sp(download_dir if len(torrent_files) == 1 else os.path.join(download_dir, torrent['name'])),
                'files': '|'.join(torrent_files),
            })

        return release_downloads

    def pause(self, release_download, pause = True):
        if pause:
            return self.drpc.pause_torrent([release_download['id']])
        else:
            return self.drpc.resume_torrent([release_download['id']])

    def removeFailed(self, release_download):
        log.info('%s failed downloading, deleting...', release_download['name'])
        return self.drpc.remove_torrent(release_download['id'], True)

    def processComplete(self, release_download, delete_files = False):
        log.debug('Requesting Deluge to remove the torrent %s%s.', (release_download['name'], ' and cleanup the downloaded files' if delete_files else ''))
        return self.drpc.remove_torrent(release_download['id'], remove_local_data = delete_files)

class DelugeRPC(object):

    host = 'localhost'
    port = 58846
    username = None
    password = None
    client = None

    def __init__(self, host = 'localhost', port = 58846, username = None, password = None):
        super(DelugeRPC, self).__init__()

        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def connect(self):
        self.client = DelugeClient()
        self.client.connect(self.host, int(self.port), self.username, self.password)

    def add_torrent_magnet(self, torrent, options):
        torrent_id = False
        try:
            self.connect()
            torrent_id = self.client.core.add_torrent_magnet(torrent, options).get()
            if not torrent_id:
                torrent_id = self._check_torrent(True, torrent)

            if torrent_id and options['label']:
                self.client.label.set_torrent(torrent_id, options['label']).get()
        except Exception, err:
            log.error('Failed to add torrent magnet %s: %s %s', (torrent, err, traceback.format_exc()))
        finally:
            if self.client:
                self.disconnect()

        return torrent_id

    def add_torrent_file(self, filename, torrent, options):
        torrent_id = False
        try:
            self.connect()
            torrent_id = self.client.core.add_torrent_file(filename, b64encode(torrent), options).get()
            if not torrent_id:
                torrent_id = self._check_torrent(False, torrent)

            if torrent_id and options['label']:
                self.client.label.set_torrent(torrent_id, options['label']).get()
        except Exception, err:
            log.error('Failed to add torrent file %s: %s %s', (filename, err, traceback.format_exc()))
        finally:
            if self.client:
                self.disconnect()

        return torrent_id

    def get_alltorrents(self):
        ret = False
        try:
            self.connect()
            ret = self.client.core.get_torrents_status({}, {}).get()
        except Exception, err:
            log.error('Failed to get all torrents: %s %s', (err, traceback.format_exc()))
        finally:
            if self.client:
                self.disconnect()
        return ret

    def pause_torrent(self, torrent_ids):
        try:
            self.connect()
            self.client.core.pause_torrent(torrent_ids).get()
        except Exception, err:
            log.error('Failed to pause torrent: %s %s', (err, traceback.format_exc()))
        finally:
            if self.client:
                self.disconnect()

    def resume_torrent(self, torrent_ids):
        try:
            self.connect()
            self.client.core.resume_torrent(torrent_ids).get()
        except Exception, err:
            log.error('Failed to resume torrent: %s %s', (err, traceback.format_exc()))
        finally:
            if self.client:
                self.disconnect()

    def remove_torrent(self, torrent_id, remove_local_data):
        ret = False
        try:
            self.connect()
            ret = self.client.core.remove_torrent(torrent_id, remove_local_data).get()
        except Exception, err:
            log.error('Failed to remove torrent: %s %s', (err, traceback.format_exc()))
        finally:
            if self.client:
                self.disconnect()
        return ret

    def disconnect(self):
        self.client.disconnect()

    def _check_torrent(self, magnet, torrent):
        # Torrent not added, check if it already existed.
        if magnet:
            torrent_hash = re.findall('urn:btih:([\w]{32,40})', torrent)[0]
        else:
            info = bdecode(torrent)["info"]
            torrent_hash = sha1(benc(info)).hexdigest()

        # Convert base 32 to hex
        if len(torrent_hash) == 32:
            torrent_hash = b16encode(b32decode(torrent_hash))

        torrent_hash = torrent_hash.lower()
        torrent_check = self.client.core.get_torrent_status(torrent_hash, {}).get()
        if torrent_check['hash']:
            return torrent_hash

        return False

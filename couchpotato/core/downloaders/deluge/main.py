from base64 import b64encode
from couchpotato.core.downloaders.base import Downloader, StatusList
from couchpotato.core.helpers.encoding import isInt, ss
from couchpotato.core.helpers.variable import tryFloat
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
from datetime import timedelta
from synchronousdeluge import DelugeClient
import os.path
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

    def download(self, data, movie, filedata = None):
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
            filename = self.createFileName(data, filedata, movie)
            remote_torrent = self.drpc.add_torrent_file(filename, b64encode(filedata), options)

        if not remote_torrent:
            log.error('Failed sending torrent to Deluge')
            return False

        log.info('Torrent sent to Deluge successfully.')
        return self.downloadReturnId(remote_torrent)

    def getAllDownloadStatus(self):

        log.debug('Checking Deluge download status.')

        if not os.path.isdir(Env.setting('from', 'renamer')):
            log.error('Renamer "from" folder doesn\'t to exist.')
            return

        if not self.connect():
            return False

        statuses = StatusList(self)

        queue = self.drpc.get_alltorrents()

        if not queue:
            log.debug('Nothing in queue or error')
            return False

        for torrent_id in queue:
            item = queue[torrent_id]
            log.debug('name=%s / id=%s / save_path=%s / move_completed_path=%s / hash=%s / progress=%s / state=%s / eta=%s / ratio=%s / stop_ratio=%s / is_seed=%s / is_finished=%s / paused=%s', (item['name'], item['hash'], item['save_path'], item['move_completed_path'], item['hash'], item['progress'], item['state'], item['eta'], item['ratio'], item['stop_ratio'], item['is_seed'], item['is_finished'], item['paused']))

            # Deluge has no easy way to work out if a torrent is stalled or failing.
            #status = 'failed'
            status = 'busy'
            if item['is_seed'] and tryFloat(item['ratio']) < tryFloat(item['stop_ratio']):
                # We have item['seeding_time'] to work out what the seeding time is, but we do not
                # have access to the downloader seed_time, as with deluge we have no way to pass it
                # when the torrent is added. So Deluge will only look at the ratio.
                # See above comment in download().
                status = 'seeding'
            elif item['is_seed'] and item['is_finished'] and item['paused'] and item['state'] == 'Paused':
                status = 'completed'

            download_dir = item['save_path']
            if item['move_on_completed']:
                download_dir = item['move_completed_path']

            statuses.append({
                'id': item['hash'],
                'name': item['name'],
                'status': status,
                'original_status': item['state'],
                'seed_ratio': item['ratio'],
                'timeleft': str(timedelta(seconds = item['eta'])),
                'folder': ss(os.path.join(download_dir, item['name'])),
            })

        return statuses

    def pause(self, item, pause = True):
        if pause:
            return self.drpc.pause_torrent([item['id']])
        else:
            return self.drpc.resume_torrent([item['id']])

    def removeFailed(self, item):
        log.info('%s failed downloading, deleting...', item['name'])
        return self.drpc.remove_torrent(item['id'], True)

    def processComplete(self, item, delete_files = False):
        log.debug('Requesting Deluge to remove the torrent %s%s.', (item['name'], ' and cleanup the downloaded files' if delete_files else ''))
        return self.drpc.remove_torrent(item['id'], remove_local_data = delete_files)

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
            if options['label']:
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
            torrent_id = self.client.core.add_torrent_file(filename, torrent, options).get()
            if options['label']:
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

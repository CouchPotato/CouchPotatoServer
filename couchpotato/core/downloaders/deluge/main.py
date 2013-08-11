from base64 import b64encode
from couchpotato.core.downloaders.base import Downloader, StatusList
from couchpotato.core.helpers.encoding import isInt
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
from datetime import timedelta

from synchronousdeluge import DelugeClient

import os.path
import traceback

log = CPLog(__name__)

class Deluge(Downloader):

    type = ['torrent', 'torrent_magnet']
    log = CPLog(__name__)

    def download(self, data, movie, filedata = None):

        log.info('Sending "%s" (%s) to Deluge.', (data.get('name'), data.get('type')))

        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        # Set parameters for Deluge
        options = {
            'add_paused': self.conf('paused', default = 0),
            'label': self.conf('label')
        }

        if len(self.conf('directory', default = '')) > 0:
            options['download_location'] = self.conf('directory', default = '')
        if len(self.conf('completed_directory', default = '')) > 0:
            options['move_completed'] = 1
            options['move_completed_path'] = self.conf('completed_directory', default = '')

        if data.get('seed_ratio'):
            options['stop_at_ratio'] = 1
            options['stop_ratio'] = tryFloat(data.get('seed_ratio'))

#        Deluge only has seed time as a global option. Might be added in
#        in a future API release.
#        if data.get('seed_time'):

        if not filedata and data.get('type') == 'torrent':
            log.error('Failed sending torrent, no data')
            return False

        # Send request to Deluge
        try:
            drpc = DelugeRPC(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))
            if data.get('type') == 'torrent_magnet':
                remote_torrent = drpc.add_torrent_magnet(data.get('url'), options)
            else:
                remote_torrent = drpc.add_torrent_file(movie, b64encode(filedata), options)

            if not remote_torrent:
                return False

            log.info('Torrent sent to Deluge successfully.')
            return self.downloadReturnId(remote_torrent)
        except:
            log.error('Failed to change settings for transfer: %s', traceback.format_exc())
            return False
        finally:
            if drpc:
                drpc.disconnect()

    def pause(self, download_info, pause = True):
        try:
            drpc = DelugeRPC(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))
            if pause:
                return drpc.pause_torrent([download_info['id']])
            else:
                return drpc.resume_torrent([download_info['id']])
        except Exception, err:
            log.error('Failed to pause torrent %s: %s', download_info['name'], err)
            return False
        finally:
            if drpc:
                drpc.disconnect()

    def removeFailed(self, item, pause = True):
        try:
            drpc = DelugeRPC(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))
            return drpc.remove_torrent(item['id'])
        except Exception, err:
            log.error('Failed to remove torrent %s: %s', item['name'], err)
            return False
        finally:
            if drpc:
                drpc.disconnect()
        

    def processComplete(self, item, delete_files = False):
        log.debug('Requesting Deluge to remove the torrent %s%s.', (item['name'], ' and cleanup the downloaded files' if delete_files else ''))
        try:
            drpc = DelugeRPC(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))
            return drpc.remove_torrent(item['id'], remove_local_data = delete_files)
        except Exception, err:
            log.error('Failed to stop and remove torrent %s: %s', item['name'], err)
            return False
        finally:
            if drpc:
                drpc.disconnect()

    def getAllDownloadStatus(self):

        log.debug('Checking Deluge download status.')

        # Load host from config and split out port.
        host = self.conf('host').split(':')
        if not isInt(host[1]):
            log.error('Config properties are not filled in correctly, port is missing.')
            return False

        # Go through Queue
        try:
            drpc = DelugeRPC(host[0], port = host[1], username = self.conf('username'), password = self.conf('password'))
            queue = drpc.get_alltorrents()
        except Exception, err:
            log.error('Failed getting queue: %s', err)
            return False
        finally:
            if drpc:
                drpc.disconnect()

        if not queue:
            return []

        statuses = StatusList(self)

        for torrent_id in queue:
            item = queue[torrent_id]
            log.debug('name=%s / id=%s / save_path=%s / hash=%s / progress=%s / state=%s / eta=%s / ratio=%s / conf_ratio=%s/ is_seed=%s / is_finished=%s', (item['name'], item['hash'], item['save_path'], item['hash'], item['progress'], item['state'], item['eta'], item['ratio'], self.conf('ratio'), item['is_seed'], item['is_finished']))

            if not os.path.isdir(Env.setting('from', 'renamer')):
                log.error('Renamer "from" folder doesn\'t to exist.')
                return

            status = 'busy'
            # Deluge seems to set both is_seed and is_finished once everything has been downloaded.
            if item['is_seed'] or item['is_finished']:
            		status = 'seeding'
            elif item['is_seed'] and item['is_finished'] and item['paused']:
                status = 'completed'

            download_dir = item['save_path']
            if item['move_on_completed']:
                download_dir = item['move_completed_path']

            statuses.append({
                'id': item['hash'],
                'name': item['name'],
                'status': status,
                'original_status': item['state'],
                'timeleft': str(timedelta(seconds = item['eta'])),
                'folder': os.path.join(download_dir, item['name']),
            })

        return statuses

class DelugeRPC(object):

    client = None

    def __init__(self, host = 'localhost', port = 58846, username = None, password = None):
        super(DelugeRPC, self).__init__()
        self.client = DelugeClient()
        self.client.connect(host, int(port), username, password)

    def add_torrent_magnet(self, torrent, options):
        torrent_id = self.client.core.add_torrent_magnet(torrent, options).get()
        if options['label']:
            self.client.label.set_torrent(torrent_id, options['label']).get()

        return torrent_id

    def add_torrent_file(self, movie, torrent, options):
        torrent_id = self.client.core.add_torrent_file(movie, torrent, options).get()
        if options['label']:
            self.client.label.set_torrent(torrent_id, options['label']).get()

        return torrent_id

    def get_alltorrents(self):
        return self.client.core.get_torrents_status({}, {}).get()

    def pause_torrent(self, torrent_ids):
        self.client.core.pause_torrent(torrent_ids).get()

    def resume_torrent(self, torrent_ids):
        self.client.core.resume_torrent(torrent_ids).get()

    def remove_torrent(self, torrent_id, remove_local_data):
        return self.client.core.remove_torrent(torrent_id, remove_local_data).get()

    def disconnect(self):
        self.client.disconnect()

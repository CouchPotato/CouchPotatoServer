from base64 import b16encode, b32decode
from bencode import bencode, bdecode
from couchpotato.core.downloaders.base import Downloader, StatusList
from couchpotato.core.helpers.encoding import ss
from couchpotato.core.logger import CPLog
from datetime import timedelta
from hashlib import sha1
from rtorrent import RTorrent
from rtorrent.err import MethodError
import shutil

log = CPLog(__name__)


class rTorrent(Downloader):

    protocol = ['torrent', 'torrent_magnet']
    rt = None

    def connect(self):
        # Already connected?
        if self.rt is not None:
            return self.rt

        # Ensure url is set
        if not self.conf('url'):
            log.error('Config properties are not filled in correctly, url is missing.')
            return False

        if self.conf('username') and self.conf('password'):
            self.rt = RTorrent(
                self.conf('url'),
                self.conf('username'),
                self.conf('password')
            )
        else:
            self.rt = RTorrent(self.conf('url'))

        return self.rt

    def _update_provider_group(self, name, data):
        if data.get('seed_time'):
            log.info('seeding time ignored, not supported')

        if not name:
            return False

        if not self.connect():
            return False

        views = self.rt.get_views()

        if name not in views:
            self.rt.create_group(name)

        group = self.rt.get_group(name)

        try:
            if data.get('seed_ratio'):
                ratio = int(float(data.get('seed_ratio')) * 100)
                log.debug('Updating provider ratio to %s, group name: %s', (ratio, name))

                # Explicitly set all group options to ensure it is setup correctly
                group.set_upload('1M')
                group.set_min(ratio)
                group.set_max(ratio)
                group.set_command('d.stop')
                group.enable()
            else:
                # Reset group action and disable it
                group.set_command()
                group.disable()
        except MethodError, err:
            log.error('Unable to set group options: %s', err.message)
            return False

        return True


    def download(self, data, movie, filedata = None):
        log.debug('Sending "%s" to rTorrent.', (data.get('name')))

        if not self.connect():
            return False

        group_name = 'cp_' + data.get('provider').lower()
        if not self._update_provider_group(group_name, data):
            return False

        torrent_params = {}
        if self.conf('label'):
            torrent_params['label'] = self.conf('label')

        if not filedata and data.get('protocol') == 'torrent':
            log.error('Failed sending torrent, no data')
            return False

        # Try download magnet torrents
        if data.get('protocol') == 'torrent_magnet':
            filedata = self.magnetToTorrent(data.get('url'))

            if filedata is False:
                return False

            data['protocol'] = 'torrent'

        info = bdecode(filedata)["info"]
        torrent_hash = sha1(bencode(info)).hexdigest().upper()

        # Convert base 32 to hex
        if len(torrent_hash) == 32:
            torrent_hash = b16encode(b32decode(torrent_hash))

        # Send request to rTorrent
        try:
            # Send torrent to rTorrent
            torrent = self.rt.load_torrent(filedata)

            # Set label
            if self.conf('label'):
                torrent.set_custom(1, self.conf('label'))

            # Set Ratio Group
            torrent.set_visible(group_name)

            # Start torrent
            if not self.conf('paused', default = 0):
                torrent.start()

            return self.downloadReturnId(torrent_hash)
        except Exception, err:
            log.error('Failed to send torrent to rTorrent: %s', err)
            return False

    def getAllDownloadStatus(self):
        log.debug('Checking rTorrent download status.')

        if not self.connect():
            return False

        try:
            torrents = self.rt.get_torrents()

            statuses = StatusList(self)

            for item in torrents:
                status = 'busy'
                if item.complete:
                    if item.active:
                        status = 'seeding'
                    else:
                        status = 'completed'

                statuses.append({
                    'id': item.info_hash,
                    'name': item.name,
                    'status': status,
                    'seed_ratio': item.ratio,
                    'original_status': item.state,
                    'timeleft': str(timedelta(seconds = float(item.left_bytes) / item.down_rate)) if item.down_rate > 0 else -1,
                    'folder': ss(item.directory)
                })

            return statuses

        except Exception, err:
            log.error('Failed to get status from rTorrent: %s', err)
            return False

    def pause(self, download_info, pause = True):
        if not self.connect():
            return False

        torrent = self.rt.find_torrent(download_info['id'])
        if torrent is None:
            return False

        if pause:
            return torrent.pause()
        return torrent.resume()

    def removeFailed(self, item):
        log.info('%s failed downloading, deleting...', item['name'])
        return self.processComplete(item, delete_files = True)

    def processComplete(self, item, delete_files):
        log.debug('Requesting rTorrent to remove the torrent %s%s.',
                  (item['name'], ' and cleanup the downloaded files' if delete_files else ''))
        if not self.connect():
            return False

        torrent = self.rt.find_torrent(item['id'])
        if torrent is None:
            return False

        torrent.erase() # just removes the torrent, doesn't delete data

        if delete_files:
            shutil.rmtree(item['folder'], True)

        return True

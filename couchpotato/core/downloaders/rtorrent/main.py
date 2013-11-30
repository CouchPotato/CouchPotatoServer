from base64 import b16encode, b32decode
from bencode import bencode, bdecode
from couchpotato.core.downloaders.base import Downloader, ReleaseDownloadList
from couchpotato.core.helpers.encoding import sp
from couchpotato.core.logger import CPLog
from datetime import timedelta
from hashlib import sha1
from rtorrent import RTorrent
from rtorrent.err import MethodError
import os

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
            log.error('Unable to set group options: %s', err.msg)
            return False

        return True


    def download(self, data = None, media = None, filedata = None):
        if not media: media = {}
        if not data: data = {}

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

            if not torrent:
                log.error('Unable to find the torrent, did it fail to load?')
                return False

            # Set label
            if self.conf('label'):
                torrent.set_custom(1, self.conf('label'))

            if self.conf('directory'):
                torrent.set_directory(self.conf('directory'))

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

            release_downloads = ReleaseDownloadList(self)

            for torrent in torrents:
                torrent_files = []
                for file_item in torrent.get_files():
                    torrent_files.append(sp(os.path.join(torrent.directory, file_item.path)))

                status = 'busy'
                if torrent.complete:
                    if torrent.active:
                        status = 'seeding'
                    else:
                        status = 'completed'

                release_downloads.append({
                    'id': torrent.info_hash,
                    'name': torrent.name,
                    'status': status,
                    'seed_ratio': torrent.ratio,
                    'original_status': torrent.state,
                    'timeleft': str(timedelta(seconds = float(torrent.left_bytes) / torrent.down_rate)) if torrent.down_rate > 0 else -1,
                    'folder': sp(torrent.directory),
                    'files': '|'.join(torrent_files)
                })

            return release_downloads

        except Exception, err:
            log.error('Failed to get status from rTorrent: %s', err)
            return False

    def pause(self, release_download, pause = True):
        if not self.connect():
            return False

        torrent = self.rt.find_torrent(release_download['id'])
        if torrent is None:
            return False

        if pause:
            return torrent.pause()
        return torrent.resume()

    def removeFailed(self, release_download):
        log.info('%s failed downloading, deleting...', release_download['name'])
        return self.processComplete(release_download, delete_files = True)

    def processComplete(self, release_download, delete_files):
        log.debug('Requesting rTorrent to remove the torrent %s%s.',
                  (release_download['name'], ' and cleanup the downloaded files' if delete_files else ''))

        if not self.connect():
            return False

        torrent = self.rt.find_torrent(release_download['id'])

        if torrent is None:
            return False

        if delete_files:
            for file_item in torrent.get_files(): # will only delete files, not dir/sub-dir
                os.unlink(os.path.join(torrent.directory, file_item.path))

            if torrent.is_multi_file() and torrent.directory.endswith(torrent.name):
                # Remove empty directories bottom up
                try:
                    for path, _, _ in os.walk(torrent.directory, topdown = False):
                        os.rmdir(path)
                except OSError:
                    log.info('Directory "%s" contains extra files, unable to remove', torrent.directory)

        torrent.erase() # just removes the torrent, doesn't delete data

        return True

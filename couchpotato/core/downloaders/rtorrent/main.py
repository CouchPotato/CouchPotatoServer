from base64 import b16encode, b32decode
from bencode import bencode, bdecode
from couchpotato.core.downloaders.base import Downloader, ReleaseDownloadList
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.encoding import sp
from couchpotato.core.helpers.variable import cleanHost, splitString
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
    testable = True

    # Migration url to host options
    def __init__(self):
        super(rTorrent, self).__init__()

        addEvent('app.load', self.migrate)

    def migrate(self):

        url = self.conf('url')
        if url:
            host_split = splitString(url.split('://')[-1], split_on = '/')

            self.conf('ssl', value = url.startswith('https'))
            self.conf('host', value = host_split[0].strip())
            self.conf('rpc_url', value = '/'.join(host_split[1:]))

            self.deleteConf('url')

    def connect(self, reconnect = False):
        # Already connected?
        if not reconnect and self.rt is not None:
            return self.rt

        url = cleanHost(self.conf('host'), protocol = True, ssl = self.conf('ssl')) + self.conf('rpc_url')

        if self.conf('username') and self.conf('password'):
            self.rt = RTorrent(
                url,
                self.conf('username'),
                self.conf('password')
            )
        else:
            self.rt = RTorrent(url)

        if not self.rt.test_connection():
            self.rt = None

        return self.rt

    def test(self):
        if not self.connect(True):
            return False
        return True

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
        except MethodError as err:
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
            torrent = self.rt.load_torrent(filedata, verify_retries=10)

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
        except Exception as err:
            log.error('Failed to send torrent to rTorrent: %s', err)
            return False

    def getAllDownloadStatus(self, ids):
        log.debug('Checking rTorrent download status.')

        if not self.connect():
            return []

        try:
            torrents = self.rt.get_torrents()

            release_downloads = ReleaseDownloadList(self)

            for torrent in torrents:
                if torrent.info_hash in ids:
                    torrent_directory = os.path.normpath(torrent.directory)
                    torrent_files = []

                    for file in torrent.get_files():
                        if not os.path.normpath(file.path).startswith(torrent_directory):
                            file_path = os.path.join(torrent_directory, file.path.lstrip('/'))
                        else:
                            file_path = file.path

                        torrent_files.append(sp(file_path))

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

        except Exception as err:
            log.error('Failed to get status from rTorrent: %s', err)
            return []

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

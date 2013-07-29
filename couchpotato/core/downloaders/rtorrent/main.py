from base64 import b16encode, b32decode
from datetime import timedelta
from hashlib import sha1
import traceback

from bencode import bencode, bdecode
from couchpotato.core.downloaders.base import Downloader, StatusList
from couchpotato.core.logger import CPLog
from rtorrent import RTorrent


log = CPLog(__name__)


class rTorrent(Downloader):

    type = ['torrent', 'torrent_magnet']
    rtorrent_api = None

    def get_conn(self):
        if self.conf('username') and self.conf('password'):
            return RTorrent(
                self.conf('url'),
                self.conf('username'),
                self.conf('password')
            )

        return RTorrent(self.conf('url'))

    def download(self, data, movie, filedata=None):
        log.debug('Sending "%s" (%s) to rTorrent.', (data.get('name'), data.get('type')))

        torrent_params = {}
        if self.conf('label'):
            torrent_params['label'] = self.conf('label')

        if not filedata and data.get('type') == 'torrent':
            log.error('Failed sending torrent, no data')
            return False

        # Try download magnet torrents
        if data.get('type') == 'torrent_magnet':
            filedata = self.magnetToTorrent(data.get('url'))

            if filedata is False:
                return False

            data['type'] = 'torrent'

        info = bdecode(filedata)["info"]
        torrent_hash = sha1(bencode(info)).hexdigest().upper()

        # Convert base 32 to hex
        if len(torrent_hash) == 32:
            torrent_hash = b16encode(b32decode(torrent_hash))

        # Send request to rTorrent
        try:
            if not self.rtorrent_api:
                self.rtorrent_api = self.get_conn()

            # Send torrent to rTorrent
            torrent = self.rtorrent_api.load_torrent(filedata)

            # Set label
            if self.conf('label'):
                torrent.set_custom(1, self.conf('label'))

            # Start torrent
            if not self.conf('paused', default=0):
                torrent.start()

            return self.downloadReturnId(torrent_hash)
        except Exception, err:
            log.error('Failed to send torrent to rTorrent: %s', err)
            return False


    def getAllDownloadStatus(self):

        log.debug('Checking rTorrent download status.')

        try:
            if not self.rtorrent_api:
                self.rtorrent_api = self.get_conn()

            torrents = self.rtorrent_api.get_torrents()

            statuses = StatusList(self)

            for item in torrents:
                statuses.append({
                    'id': item.info_hash,
                    'name': item.name,
                    'status': 'completed' if item.complete else 'busy',
                    'original_status': item.state,
                    'timeleft': str(timedelta(seconds=float(item.left_bytes) / item.down_rate))
                                    if item.down_rate > 0 else -1,
                    'folder': item.directory
                })

            return statuses

        except Exception, err:
            log.error('Failed to get status from rTorrent: %s', err)
            return False

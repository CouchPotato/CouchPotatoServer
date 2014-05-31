from base64 import b16encode, b32decode
from hashlib import sha1
import os

from bencode import bencode, bdecode
from couchpotato.core._base.downloader.main import DownloaderBase, ReleaseDownloadList
from couchpotato.core.helpers.encoding import sp
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from qbittorrent.client import QBittorrentClient


log = CPLog(__name__)

autoload = 'qBittorrent'


class qBittorrent(DownloaderBase):

    protocol = ['torrent', 'torrent_magnet']
    qb = None

    def __init__(self):
        super(qBittorrent, self).__init__()

    def connect(self):
        if self.qb is not None:
            return self.qb

        url = cleanHost(self.conf('host'), protocol = True, ssl = False)

        if self.conf('username') and self.conf('password'):
            self.qb = QBittorrentClient(
                url,
                username = self.conf('username'),
                password = self.conf('password')
            )
        else:
            self.qb = QBittorrentClient(url)

        return self.qb

    def test(self):
        if self.connect():
            return True

        return False

    def download(self, data = None, media = None, filedata = None):
        if not media: media = {}
        if not data: data = {}

        log.debug('Sending "%s" to qBittorrent.', (data.get('name')))

        if not self.connect():
            return False

        if not filedata and data.get('protocol') == 'torrent':
            log.error('Failed sending torrent, no data')
            return False


        if data.get('protocol') == 'torrent_magnet':
            filedata = self.magnetToTorrent(data.get('url'))

            if filedata is False:
                return False

            data['protocol'] = 'torrent'

        info = bdecode(filedata)["info"]
        torrent_hash = sha1(bencode(info)).hexdigest()

        # Convert base 32 to hex
        if len(torrent_hash) == 32:
            torrent_hash = b16encode(b32decode(torrent_hash))

        # Send request to qBittorrent
        try:
            self.qb.add_file(filedata)

            return self.downloadReturnId(torrent_hash)
        except Exception as e:
            log.error('Failed to send torrent to qBittorrent: %s', e)
            return False

    def getTorrentStatus(self, torrent):

        if torrent.state in ('uploading', 'queuedUP', 'stalledUP'):
            return 'seeding'

        if torrent.progress == 1:
            return 'completed'

        return 'busy'

    def getAllDownloadStatus(self, ids):
        log.debug('Checking qBittorrent download status.')

        if not self.connect():
            return []

        try:
            torrents = self.qb.get_torrents()

            release_downloads = ReleaseDownloadList(self)

            for torrent in torrents:
                if torrent.hash in ids:
                    torrent.update_general() # get extra info
                    torrent_filelist = torrent.get_files()

                    torrent_files = []
                    torrent_dir = os.path.join(torrent.save_path, torrent.name)

                    if os.path.isdir(torrent_dir):
                        torrent.save_path = torrent_dir

                    if len(torrent_filelist) > 1 and os.path.isdir(torrent_dir): # multi file torrent, path.isdir check makes sure we're not in the root download folder
                        for root, _, files in os.walk(torrent.save_path):
                            for f in files:
                                torrent_files.append(sp(os.path.join(root, f)))

                    else: # multi or single file placed directly in torrent.save_path
                        for f in torrent_filelist:
                            file_path = os.path.join(torrent.save_path, f.name)
                            if os.path.isfile(file_path):
                                torrent_files.append(sp(file_path))

                    release_downloads.append({
                        'id': torrent.hash,
                        'name': torrent.name,
                        'status': self.getTorrentStatus(torrent),
                        'seed_ratio': torrent.ratio,
                        'original_status': torrent.state,
                        'timeleft': torrent.progress * 100 if torrent.progress else -1, # percentage
                        'folder': sp(torrent.save_path),
                        'files': torrent_files
                    })

            return release_downloads

        except Exception as e:
            log.error('Failed to get status from qBittorrent: %s', e)
            return []

    def pause(self, release_download, pause = True):
        if not self.connect():
            return False

        torrent = self.qb.get_torrent(release_download['id'])
        if torrent is None:
            return False

        if pause:
            return torrent.pause()
        return torrent.resume()

    def removeFailed(self, release_download):
        log.info('%s failed downloading, deleting...', release_download['name'])
        return self.processComplete(release_download, delete_files = True)

    def processComplete(self, release_download, delete_files):
        log.debug('Requesting qBittorrent to remove the torrent %s%s.',
                  (release_download['name'], ' and cleanup the downloaded files' if delete_files else ''))

        if not self.connect():
            return False

        torrent = self.qb.find_torrent(release_download['id'])

        if torrent is None:
            return False

        if delete_files:
            torrent.delete() # deletes torrent with data
        else:
            torrent.remove() # just removes the torrent, doesn't delete data

        return True


config = [{
    'name': 'qbittorrent',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'qbittorrent',
            'label': 'qbittorrent',
            'description': '',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'torrent',
                },
                {
                    'name': 'host',
                    'default': 'http://localhost:8080/',
                    'description': 'RPC Communication URI. Usually <strong>http://localhost:8080/</strong>'
                },
                {
                    'name': 'username',
                },
                {
                    'name': 'password',
                    'type': 'password',
                },
                {
                    'name': 'remove_complete',
                    'label': 'Remove torrent',
                    'default': False,
                    'advanced': True,
                    'type': 'bool',
                    'description': 'Remove the torrent after it finishes seeding.',
                },
                {
                    'name': 'delete_files',
                    'label': 'Remove files',
                    'default': True,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also remove the leftover files.',
                },
                {
                    'name': 'paused',
                    'type': 'bool',
                    'advanced': True,
                    'default': False,
                    'description': 'Add the torrent paused.',
                },
                {
                    'name': 'manual',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Disable this downloader for automated searches, but use it when I manually send a release.',
                },
            ],
        }
    ],
}]

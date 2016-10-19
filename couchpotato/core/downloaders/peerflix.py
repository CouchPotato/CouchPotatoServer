from base64 import b16encode, b32decode
from hashlib import sha1
from datetime import timedelta
import os
import re
import traceback

from bencode import bencode, bdecode
from couchpotato.core._base.downloader.main import DownloaderBase, ReleaseDownloadList
from couchpotato.core.helpers.encoding import sp
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.helpers.variable import getDownloadDir
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
from subprocess import Popen, PIPE


log = CPLog(__name__)

autoload = 'peerflix'



class peerflix(DownloaderBase):

    protocol = ['torrent', 'torrent_magnet']

    def __init__(self):
        super(peerflix, self).__init__()

    def connect(self):
        return True

    def test(self):
        """ Test and see if the directory is writable
        :return: boolean
        """

        directory = self.conf('directory')
        if directory and os.path.isdir(directory):

            test_file = sp(os.path.join(directory, 'couchpotato_test.txt'))

            # Check if folder is writable
            self.createFile(test_file, 'This is a test file')
            if os.path.isfile(test_file):
                os.remove(test_file)
                return True

        return False

    def download(self, data = None, media = None, filedata = None):
        """ Send a torrent/nzb file to the downloader

        :param data: dict returned from provider
            Contains the release information
        :param media: media dict with information
            Used for creating the filename when possible
        :param filedata: downloaded torrent/nzb filedata
            The file gets downloaded in the searcher and send to this function
            This is done to have failed checking before using the downloader, so the downloader
            doesn't need to worry about that
        :return: boolean
            One fail returns false, but the downloader should log his own errors
        """

        if not media: media = {}
        if not data: data = {}

        log.debug('Sending "%s" to peerflix.', (data.get('name')))

        if not filedata and data.get('protocol') == 'torrent':
            log.error('Failed sending torrent, no data')
            return False

        torrent_hash = ''
        torrent_handle = ''
        if data.get('protocol') == 'torrent_magnet':
            torrent_handle =  data.get('url')
            torrent_hash = re.findall('urn:btih:([\w]{32,40})', data.get('url'))[0].upper()

        if data.get('protocol')  == 'torrent':
            info = bdecode(filedata)["info"]
            torrent_hash = sha1(bencode(info)).hexdigest()

            # Convert base 32 to hex
            if len(torrent_hash) == 32:
                torrent_hash = b16encode(b32decode(torrent_hash))

            # Create filename with imdb id and other nice stuff
            directory = self.conf('torrent_directory')
            file_name = self.createFileName(data, filedata, media)
            full_path = os.path.join(directory, file_name)  # Full torrent path
            # Write filedata to torrent file
            try:
                # Make sure the file doesn't exist yet, no need in overwriting it
                if not os.path.isfile(full_path):
                    log.info('Downloading %s to %s.', (data.get('protocol'), full_path))
                    with open(full_path, 'wb') as f:
                        f.write(filedata)
                    os.chmod(full_path, Env.getPermission('file'))
                else:
                    log.info('File %s already exists.', full_path)
                torrent_handle = full_path

            except:
                log.error('Failed to write .torrent file to peerflix %s', traceback.format_exc())
                pass

        peerflix_args = [self.conf('path'), torrent_handle, "-p " + self.conf('port'), "--" + self.conf('player')]
        if self.conf('movie_directory'):
            peerflix_args.append("--path '" + self.conf('movie_directory') + "'")
        if not self.conf('float_on_top'):
            peerflix_args.append('--not-on-top')
        if not self.conf('quit_peerflix_on_player_exit'):
            peerflix_args.append('--no-quit')
        if self.conf('delete_on_exit'):
            peerflix_args.append('--remove')
        if self.conf('player_options'):
            peerflix_args.append('-- ' + self.conf('player_options'))


        peerflix_args = [x.encode('utf-8') for x in peerflix_args]
        log.info('Peerflix args: "%s"', (peerflix_args))

        peerflix_proc = Popen(peerflix_args, stderr=PIPE)
        log.info('Peerflix PID: "%s"', (peerflix_proc.pid))
        log.info('Movie available for streaming at http://localhost:%s. This address can be opened in your video player.', (self.conf('port')))
        #log.error('Peerflix: %s', peerflix_proc.stderr)

        return self.downloadReturnId(torrent_hash)


    def getTorrentStatus(self, torrent):
        return 'busy'

    def getAllDownloadStatus(self, ids):
        """ Get status of all active downloads

        :param ids: list of (mixed) downloader ids
            Used to match the releases for this downloader as there could be
            other downloaders active that it should ignore
        :return: list of releases
        """

        log.info('Checking peerflix download status.')
        return []

    def pause(self, release_download, pause = True):
        return True

    def removeFailed(self, release_download):
        log.info('%s failed downloading, deleting...', release_download['name'])
        return self.processComplete(release_download, delete_files = True)

    def processComplete(self, release_download, delete_files):
        log.info('Requesting peerflix to remove the torrent %s%s.',
                  (release_download['name'], ' and cleanup the downloaded files' if delete_files else ''))
        return True


config = [{
    'name': 'peerflix',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'peerflix',
            'label': 'peerflix',
            'description': 'peerflix',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'torrent',
                },
                {
                    'name': 'player',
                    'default': 'vlc',
                    'type': 'dropdown',
                    'values': [('VLC', 'vlc'), ('MPlayer', 'mplayer'), ('SMPlayer', 'smplayer'), ('MPC-HC', 'mpchc'), ('mpv', 'mpv')],
                },
                {
                    'name': 'port',
                    'default': '8888',
                },
                {
                    'name': 'path',
                    'default': '/usr/bin/peerflix',
                    'description': "Path to Peerflix executable. If Peerflix is installed globally then usually it's /usr/bin/peerflix for Linux and XXX for Windows",
                },
                {
                    'name': 'torrent_directory',
                    'type': 'directory',
                    'description': 'Directory where the .torrent file is saved to.',
                    'default': getDownloadDir()
                },
                {
                    'name': 'movie_directory',
                    'type': 'directory',
                    'description': 'NOT WORKING. Download movies this directory. Keep empty for default Peerflix download directory, which usually is /tmp/torrent-stream/ for Linux and XXX for Windows',
                },
                {
                    'name': 'float_on_top',
                    'label': 'Float video on top',
                    'advanced': True,
                    'type': 'bool',
                    'default': False,
                },
                {
                    'name': 'quit_peerflix_on_player_exit',
                    'label': 'Quit on player exit',
                    'advanced': True,
                    'type': 'bool',
                    'default': False,
                    'description': 'Quit downloading with Peerflix when closing video player',
                },
                {
                    'name': 'delete_on_exit',
                    'label': 'Delete on exit',
                    'advanced': True,
                    'type': 'bool',
                    'default': False,
                    'description': 'Delete movie file(s) when Peerflix exits.',
                },
                {
                    'name': 'player_options',
                    'advanced': True,
                    'description': 'Options passed along to video player. E.g. --fullscreen --subtitles=/home/subtitle.srt',
                },
            ],
        }
    ],
}]

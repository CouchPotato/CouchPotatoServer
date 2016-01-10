from __future__ import with_statement
import os
import traceback

from couchpotato.core._base.downloader.main import DownloaderBase
from couchpotato.core.helpers.encoding import sp
from couchpotato.core.helpers.variable import getDownloadDir
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env


log = CPLog(__name__)

autoload = 'Blackhole'


class Blackhole(DownloaderBase):

    protocol = ['nzb', 'torrent', 'torrent_magnet']
    status_support = False

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
            One faile returns false, but the downloaded should log his own errors
        """

        if not media: media = {}
        if not data: data = {}

        directory = self.conf('directory')

        # The folder needs to exist
        if not directory or not os.path.isdir(directory):
            log.error('No directory set for blackhole %s download.', data.get('protocol'))
        else:
            try:
                # Filedata can be empty, which probably means it a magnet link
                if not filedata or len(filedata) < 50:
                    try:
                        if data.get('protocol') == 'torrent_magnet':
                            filedata = self.magnetToTorrent(data.get('url'))
                            data['protocol'] = 'torrent'
                    except:
                        log.error('Failed download torrent via magnet url: %s', traceback.format_exc())

                    # If it's still empty, either write the magnet link to a .magnet file, or error out.
                    if not filedata or len(filedata) < 50:
                        if self.conf('magnet_file'):
                            filedata = data.get('url') + '\n'
                            data['protocol'] = 'magnet'
                        else:
                            log.error('No nzb/torrent available: %s', data.get('url'))
                            return False

                # Create filename with imdb id and other nice stuff
                file_name = self.createFileName(data, filedata, media)
                full_path = os.path.join(directory, file_name)

                # People want thinks nice and tidy, create a subdir
                if self.conf('create_subdir'):
                    try:
                        new_path = os.path.splitext(full_path)[0]
                        if not os.path.exists(new_path):
                            os.makedirs(new_path)
                            full_path = os.path.join(new_path, file_name)
                    except:
                        log.error('Couldnt create sub dir, reverting to old one: %s', full_path)

                try:

                    # Make sure the file doesn't exist yet, no need in overwriting it
                    if not os.path.isfile(full_path):
                        log.info('Downloading %s to %s.', (data.get('protocol'), full_path))
                        with open(full_path, 'wb') as f:
                            f.write(filedata)
                        os.chmod(full_path, Env.getPermission('file'))
                        return self.downloadReturnId('')
                    else:
                        log.info('File %s already exists.', full_path)
                        return self.downloadReturnId('')

                except:
                    log.error('Failed to download to blackhole %s', traceback.format_exc())
                    pass

            except:
                log.info('Failed to download file %s: %s', (data.get('name'), traceback.format_exc()))
                return False

        return False

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

    def getEnabledProtocol(self):
        """ What protocols is this downloaded used for
        :return: list with protocols
        """

        if self.conf('use_for') == 'both':
            return super(Blackhole, self).getEnabledProtocol()
        elif self.conf('use_for') == 'torrent':
            return ['torrent', 'torrent_magnet']
        else:
            return ['nzb']

    def isEnabled(self, manual = False, data = None):
        """ Check if protocol is used (and enabled)
        :param manual: The user has clicked to download a link through the webUI
        :param data: dict returned from provider
            Contains the release information
        :return: boolean
        """
        if not data: data = {}
        for_protocol = ['both']
        if data and 'torrent' in data.get('protocol'):
            for_protocol.append('torrent')
        elif data:
            for_protocol.append(data.get('protocol'))

        return super(Blackhole, self).isEnabled(manual, data) and \
            ((self.conf('use_for') in for_protocol))


config = [{
    'name': 'blackhole',
    'order': 30,
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'blackhole',
            'label': 'Black hole',
            'description': 'Download the NZB/Torrent to a specific folder. <em>Note: Seeding and copying/linking features do <strong>not</strong> work with Black hole</em>.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': True,
                    'type': 'enabler',
                    'radio_group': 'nzb,torrent',
                },
                {
                    'name': 'directory',
                    'type': 'directory',
                    'description': 'Directory where the .nzb (or .torrent) file is saved to.',
                    'default': getDownloadDir()
                },
                {
                    'name': 'use_for',
                    'label': 'Use for',
                    'default': 'both',
                    'type': 'dropdown',
                    'values': [('usenet & torrents', 'both'), ('usenet', 'nzb'), ('torrent', 'torrent')],
                },
                {
                    'name': 'create_subdir',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Create a sub directory when saving the .nzb (or .torrent).',
                },
                {
                    'name': 'manual',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Disable this downloader for automated searches, but use it when I manually send a release.',
                },
                {
                    'name': 'magnet_file',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'If magnet file conversion fails, write down the magnet link in a .magnet file instead.',
                },
            ],
        }
    ],
}]

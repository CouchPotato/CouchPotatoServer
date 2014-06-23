from __future__ import with_statement
import os
import traceback

from couchpotato.core._base.downloader.main import DownloaderBase
from couchpotato.core.helpers.encoding import sp
from couchpotato.core.logger import CPLog


log = CPLog(__name__)

autoload = 'Pneumatic'


class Pneumatic(DownloaderBase):

    protocol = ['nzb']
    strm_syntax = 'plugin://plugin.program.pneumatic/?mode=strm&type=add_file&nzb=%s&nzbname=%s'
    status_support = False

    def download(self, data = None, media = None, filedata = None):
        if not media: media = {}
        if not data: data = {}

        directory = self.conf('directory')
        if not directory or not os.path.isdir(directory):
            log.error('No directory set for .strm downloads.')
        else:
            try:
                if not filedata or len(filedata) < 50:
                    log.error('No nzb available!')
                    return False

                full_path = os.path.join(directory, self.createFileName(data, filedata, media))

                try:
                    if not os.path.isfile(full_path):
                        log.info('Downloading %s to %s.', (data.get('protocol'), full_path))
                        with open(full_path, 'wb') as f:
                            f.write(filedata)

                        nzb_name = self.createNzbName(data, media)
                        strm_path = os.path.join(directory, nzb_name)

                        strm_file = open(strm_path + '.strm', 'wb')
                        strmContent = self.strm_syntax % (full_path, nzb_name)
                        strm_file.write(strmContent)
                        strm_file.close()

                        return self.downloadReturnId('')

                    else:
                        log.info('File %s already exists.', full_path)
                        return self.downloadReturnId('')

                except:
                    log.error('Failed to download .strm: %s', traceback.format_exc())
                    pass

            except:
                log.info('Failed to download file %s: %s', (data.get('name'), traceback.format_exc()))
                return False
        return False

    def test(self):
        directory = self.conf('directory')
        if directory and os.path.isdir(directory):

            test_file = sp(os.path.join(directory, 'couchpotato_test.txt'))

            # Check if folder is writable
            self.createFile(test_file, 'This is a test file')
            if os.path.isfile(test_file):
                os.remove(test_file)
                return True

        return False


config = [{
    'name': 'pneumatic',
    'order': 30,
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'pneumatic',
            'label': 'Pneumatic',
            'description': 'Use <a href="http://forum.xbmc.org/showthread.php?tid=97657" target="_blank">Pneumatic</a> to download .strm files.',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'directory',
                    'type': 'directory',
                    'description': 'Directory where the .strm file is saved to.',
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

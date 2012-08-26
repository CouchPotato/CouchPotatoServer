from __future__ import with_statement
from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.logger import CPLog
import os
import traceback

log = CPLog(__name__)

class Blackhole(Downloader):

    type = ['nzb', 'torrent', 'torrent_magnet']

    def download(self, data = {}, movie = {}, manual = False, filedata = None):
        if self.isDisabled(manual) or (not self.isCorrectType(data.get('type')) or (not self.conf('use_for') in ['both', data.get('type')])):
            return

        directory = self.conf('directory')
        if not directory or not os.path.isdir(directory):
            log.error('No directory set for blackhole %s download.', data.get('type'))
        else:
            try:
                if not filedata or len(filedata) < 50:
                    try:
                        if data.get('type') == 'torrent_magnet':
                            filedata = self.magnetToTorrent(data.get('url'))
                            data['type'] = 'torrent'
                    except:
                        log.error('Failed download torrent via magnet url: %s', traceback.format_exc())

                    if not filedata or len(filedata) < 50:
                        log.error('No nzb/torrent available: %s', data.get('url'))
                        return False

                fullPath = os.path.join(directory, self.createFileName(data, filedata, movie))

                try:
                    if not os.path.isfile(fullPath):
                        log.info('Downloading %s to %s.', (data.get('type'), fullPath))
                        with open(fullPath, 'wb') as f:
                            f.write(filedata)
                        return True
                    else:
                        log.info('File %s already exists.', fullPath)
                        return True

                except:
                    log.error('Failed to download to blackhole %s', traceback.format_exc())
                    pass

            except:
                log.info('Failed to download file %s: %s', (data.get('name'), traceback.format_exc()))
                return False
        return False

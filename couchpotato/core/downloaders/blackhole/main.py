from __future__ import with_statement
from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
import os
import traceback

log = CPLog(__name__)


class Blackhole(Downloader):

    protocol = ['nzb', 'torrent', 'torrent_magnet']

    def download(self, data = None, movie = None, filedata = None):
        if not movie: movie = {}
        if not data: data = {}

        directory = self.conf('directory')
        if not directory or not os.path.isdir(directory):
            log.error('No directory set for blackhole %s download.', data.get('protocol'))
        else:
            try:
                if not filedata or len(filedata) < 50:
                    try:
                        if data.get('protocol') == 'torrent_magnet':
                            filedata = self.magnetToTorrent(data.get('url'))
                            data['protocol'] = 'torrent'
                    except:
                        log.error('Failed download torrent via magnet url: %s', traceback.format_exc())

                    if not filedata or len(filedata) < 50:
                        log.error('No nzb/torrent available: %s', data.get('url'))
                        return False

                fullPath = os.path.join(directory, self.createFileName(data, filedata, movie))

                try:
                    if not os.path.isfile(fullPath):
                        log.info('Downloading %s to %s.', (data.get('protocol'), fullPath))
                        with open(fullPath, 'wb') as f:
                            f.write(filedata)
                        os.chmod(fullPath, Env.getPermission('file'))
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

    def getEnabledProtocol(self):
        if self.conf('use_for') == 'both':
            return super(Blackhole, self).getEnabledProtocol()
        elif self.conf('use_for') == 'torrent':
            return ['torrent', 'torrent_magnet']
        else:
            return ['nzb']

    def isEnabled(self, manual = False, data = None):
        if not data: data = {}
        for_protocol = ['both']
        if data and 'torrent' in data.get('protocol'):
            for_protocol.append('torrent')
        elif data:
            for_protocol.append(data.get('protocol'))

        return super(Blackhole, self).isEnabled(manual, data) and \
            ((self.conf('use_for') in for_protocol))

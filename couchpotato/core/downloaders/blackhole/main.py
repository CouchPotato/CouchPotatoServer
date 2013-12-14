from __future__ import with_statement
from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
import os
import traceback

log = CPLog(__name__)


class Blackhole(Downloader):

    protocol = ['nzb', 'torrent', 'torrent_magnet']

    def download(self, data = None, media = None, filedata = None):
        if not media: media = {}
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

                file_name = self.createFileName(data, filedata, media)
                full_path = os.path.join(directory, file_name)

                if self.conf('create_subdir'):
                    try:
                        new_path = os.path.splitext(full_path)[0]
                        if not os.path.exists(new_path):
                            os.makedirs(new_path)
                            full_path = os.path.join(new_path, file_name)
                    except:
                        log.error('Couldnt create sub dir, reverting to old one: %s', full_path)

                try:
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

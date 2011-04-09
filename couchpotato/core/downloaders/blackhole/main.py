from __future__ import with_statement
from couchpotato.core.helpers.encoding import toSafeString
from couchpotato.core.logger import CPLog
from couchpotato.core.downloaders.base import Downloader
import os
import urllib

log = CPLog(__name__)

class Blackhole(Downloader):

    type = ['nzb', 'torrent']

    def download(self, data = {}):

        if self.isDisabled() or not self.isCorrectType(data.get('type')):
            return

        directory = self.conf('directory')

        if not directory or not os.path.isdir(directory):
            log.error('No directory set for blackhole %s download.' % data.get('type'))
        else:
            fullPath = os.path.join(directory, toSafeString(data.get('name')) + '.' + data)

            if not os.path.isfile(fullPath):
                log.info('Downloading %s to %s.' % (data.get('type'), fullPath))
                file = urllib.urlopen(data.get('url')).read()
                with open(fullPath, 'wb') as f:
                    f.write(file)

                return True
            else:
                log.error('File %s already exists.' % fullPath)

        return False

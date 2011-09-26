from couchpotato.core.downloaders.base import Downloader
from couchpotato.core.helpers.encoding import toSafeString
from couchpotato.core.logger import CPLog
import os
import traceback

log = CPLog(__name__)

class Blackhole(Downloader):

    type = ['nzb', 'torrent']

    def download(self, data = {}, movie = {}):

        if self.isDisabled() or not self.isCorrectType(data.get('type')):
            return

        directory = self.conf('directory')

        if not directory or not os.path.isdir(directory):
            log.error('No directory set for blackhole %s download.' % data.get('type'))
        else:
            fullPath = os.path.join(directory, '%s%s.%s' % (toSafeString(data.get('name')), self.cpTag(movie) , data.get('type')))

            try:
                if not os.path.isfile(fullPath):
                    log.info('Downloading %s to %s.' % (data.get('type'), fullPath))

                    try:
                        file = data.get('download')(url = data.get('url'), nzb_id = data.get('id'))

                        with open(fullPath, 'wb') as f:
                            f.write(file)
                    except:
                        log.debug('Failed download file: %s' % data.get('name'))
                        return False

                    return True
                else:
                    log.info('File %s already exists.' % fullPath)
                    return True
            except:
                log.error('Failed to download to blackhole %s' % traceback.format_exc())
                pass

        return False

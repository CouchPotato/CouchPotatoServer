from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import getExt, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
import os

log = CPLog(__name__)


class Trailer(Plugin):

    def __init__(self):
        addEvent('renamer.after', self.searchSingle)

    def searchSingle(self, group):

        if self.isDisabled() or len(group['files']['trailer']) > 0: return

        trailers = fireEvent('trailer.search', group = group, merge = True)
        if not trailers or trailers == []:
            log.info('No trailers found for: %s', getTitle(group['library']))
            return

        for trailer in trailers.get(self.conf('quality'), []):
            destination = '%s-trailer.%s' % (self.getRootName(group), getExt(trailer))
            if not os.path.isfile(destination):
                fireEvent('file.download', url = trailer, dest = destination, urlopen_kwargs = {'headers': {'User-Agent': 'Quicktime'}}, single = True)
            else:
                log.debug('Trailer already exists: %s', destination)

            # Download first and break
            break

    def getRootName(self, data = {}):
        return os.path.join(data['destination_dir'], data['filename'])

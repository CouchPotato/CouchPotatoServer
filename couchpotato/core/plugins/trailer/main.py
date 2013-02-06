from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import getExt, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
import os

log = CPLog(__name__)


class Trailer(Plugin):

    def __init__(self):
        addEvent('renamer.after', self.searchSingle)

    def searchSingle(self, message = None, group = {}):

        if self.isDisabled() or len(group['files']['trailer']) > 0: return

        trailers = fireEvent('trailer.search', group = group, merge = True)
        if not trailers or trailers == []:
            log.info('No trailers found for: %s', getTitle(group['library']))
            return False

        for trailer in trailers.get(self.conf('quality'), []):
            filename = self.conf('name').replace('<filename>', group['filename']) + ('.%s' % getExt(trailer))
            destination = os.path.join(group['destination_dir'], filename)
            if not os.path.isfile(destination):
                fireEvent('file.download', url = trailer, dest = destination, urlopen_kwargs = {'headers': {'User-Agent': 'Quicktime'}}, single = True)
            else:
                log.debug('Trailer already exists: %s', destination)

            group['renamed_files'].append(destination)

            # Download first and break
            break

        return True


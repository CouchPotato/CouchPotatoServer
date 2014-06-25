import os

from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import getExt, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin


log = CPLog(__name__)

autoload = 'Trailer'


class Trailer(Plugin):

    def __init__(self):
        addEvent('renamer.after', self.searchSingle)

    def searchSingle(self, message = None, group = None):
        if not group: group = {}
        if self.isDisabled() or len(group['files']['trailer']) > 0: return

        trailers = fireEvent('trailer.search', group = group, merge = True)
        if not trailers or trailers == []:
            log.info('No trailers found for: %s', getTitle(group))
            return False

        for trailer in trailers.get(self.conf('quality'), []):

            ext = getExt(trailer)
            filename = self.conf('name').replace('<filename>', group['filename']) + ('.%s' % ('mp4' if len(ext) > 5 else ext))
            destination = os.path.join(group['destination_dir'], filename)
            if not os.path.isfile(destination):
                trailer_file = fireEvent('file.download', url = trailer, dest = destination, urlopen_kwargs = {'headers': {'User-Agent': 'Quicktime'}}, single = True)
                if trailer_file and os.path.getsize(trailer_file) < (1024 * 1024):  # Don't trust small trailers (1MB), try next one
                    os.unlink(trailer_file)
                    continue
            else:
                log.debug('Trailer already exists: %s', destination)

            group['renamed_files'].append(destination)

            # Download first and break
            break

        return True


config = [{
    'name': 'trailer',
    'groups': [
        {
            'tab': 'renamer',
            'name': 'trailer',
            'label': 'Download trailer',
            'description': 'after rename',
            'options': [
                {
                    'name': 'enabled',
                    'label': 'Search and download trailers',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'quality',
                    'default': '720p',
                    'type': 'dropdown',
                    'values': [('1080p', '1080p'), ('720p', '720p'), ('480P', '480p')],
                },
                {
                    'name': 'name',
                    'label': 'Naming',
                    'default': '<filename>-trailer',
                    'advanced': True,
                    'description': 'Use <strong>&lt;filename&gt;</strong> to use above settings.'
                },
            ],
        },
    ],
}]

from couchpotato.core.event import addEvent
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.library.base import LibraryBase


log = CPLog(__name__)

autoload = 'MovieLibraryPlugin'


class MovieLibraryPlugin(LibraryBase):

    def __init__(self):
        addEvent('library.query', self.query)

    def query(self, media, first = True, include_year = True, **kwargs):
        if media.get('type') != 'movie':
            return

        default_title = getTitle(media)
        titles = media['info'].get('titles', [])
        titles.insert(0, default_title)

        # Add year identifier to titles
        if include_year:
            titles = [title + (' %s' % str(media['info']['year'])) for title in titles]

        if first:
            return titles[0] if titles else None

        return titles

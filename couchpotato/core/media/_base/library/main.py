from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.media._base.library.base import LibraryBase


class Library(LibraryBase):
    def __init__(self):
        addEvent('library.title', self.title)

    def title(self, library):
        return fireEvent(
            'library.query',
            library,

            condense = False,
            include_year = False,
            include_identifier = False,
            single = True
        )

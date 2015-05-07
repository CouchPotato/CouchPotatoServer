from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.library.base import LibraryBase

log = CPLog(__name__)

autoload = 'SeasonLibraryPlugin'


class SeasonLibraryPlugin(LibraryBase):
    def __init__(self):
        addEvent('library.query', self.query)
        addEvent('library.identifier', self.identifier)

    def query(self, media, first = True, condense = True, include_identifier = True, **kwargs):
        if media.get('type') != 'show.season':
            return

        related = fireEvent('library.related', media, single = True)

        # Get show titles
        titles = fireEvent(
            'library.query', related['show'],

            first = False,
            condense = condense,

            single = True
        )

        # TODO map_names

        # Add season identifier to titles
        if include_identifier:
            identifier = fireEvent('library.identifier', media, single = True)

            if identifier and identifier.get('season') is not None:
                titles = [title + (' S%02d' % identifier['season']) for title in titles]

        if first:
            return titles[0] if titles else None

        return titles

    def identifier(self, media):
        if media.get('type') != 'show.season':
            return

        return {
            'season': tryInt(media['info']['number'], None)
        }

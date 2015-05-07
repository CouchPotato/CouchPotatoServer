from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.library.base import LibraryBase
from qcond import QueryCondenser

log = CPLog(__name__)

autoload = 'ShowLibraryPlugin'


class ShowLibraryPlugin(LibraryBase):
    query_condenser = QueryCondenser()

    def __init__(self):
        addEvent('library.query', self.query)

    def query(self, media, first = True, condense = True, include_identifier = True, **kwargs):
        if media.get('type') != 'show':
            return

        titles = media['info']['titles']

        if condense:
            # Use QueryCondenser to build a list of optimal search titles
            condensed_titles = self.query_condenser.distinct(titles)

            if condensed_titles:
                # Use condensed titles if we got a valid result
                titles = condensed_titles
            else:
                # Fallback to simplifying titles
                titles = [simplifyString(title) for title in titles]

        if first:
            return titles[0] if titles else None

        return titles

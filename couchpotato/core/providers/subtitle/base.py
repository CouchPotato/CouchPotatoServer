from couchpotato.core.event import addEvent
from couchpotato.core.providers.base import Provider


class SubtitleProvider(Provider):

    type = 'subtitle'

    def __init__(self):
        addEvent('subtitle.search', self.search)

    def search(self, group):
        pass

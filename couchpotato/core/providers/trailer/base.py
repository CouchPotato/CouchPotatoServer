from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import Provider

log = CPLog(__name__)


class TrailerProvider(Provider):

    type = 'trailer'

    def __init__(self):
        addEvent('trailer.search', self.search)

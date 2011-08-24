from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class MetaData(Plugin):

    def __init__(self):
        addEvent('renaming.after', self.add)

        addEvent('app.load', self.add)

    def add(self, data = {}):
        log.info('Getting meta data')

        fireEvent('metadata.create', data)

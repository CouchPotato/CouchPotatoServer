from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class Wizard(Plugin):

    def __init__(self):
        self.registerStatic(__file__)

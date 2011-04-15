from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class Wizard(Plugin):

    def __init__(self):
        path = self.registerStatic(__file__)
        fireEvent('register_script', path + 'spotlight.js')
        fireEvent('register_script', path + 'wizard.js')

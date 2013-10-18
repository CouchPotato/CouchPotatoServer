from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
import os

log = CPLog(__name__)


class Custom(Plugin):

    def __init__(self):
        addEvent('app.load', self.createStructure)

    def createStructure(self):

        custom_dir = os.path.join(Env.get('data_dir'), 'custom_plugins')

        if not os.path.isdir(custom_dir):
            self.makeDir(custom_dir)
            self.createFile(os.path.join(custom_dir, '__init__.py'), '# Don\'t remove this file')

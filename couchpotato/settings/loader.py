from blinker import signal
from couchpotato.core.logger import CPLog
import glob
import os
import sys

log = CPLog(__name__)

class SettingsLoader:

    def __init__(self, root = ''):

        self.register = signal('settings_register')

        self.paths = {
            'plugins' : ('couchpotato.core.plugins', os.path.join(root, 'couchpotato', 'core', 'plugins')),
            'providers' : ('couchpotato.core.providers', os.path.join(root, 'couchpotato', 'core', 'providers')),
        }

        for type, tuple in self.paths.iteritems():
            self.loadFromDir(tuple[0], tuple[1])

    def loadFromDir(self, module, dir):
        for file in glob.glob(os.path.join(dir, '*')):
            plugin_name = os.path.basename(file)
            plugin_dir = os.path.join(dir, plugin_name)
            if os.path.isdir(plugin_dir):
                self.loadConfig(module, plugin_name)

    def loadConfig(self, module, name):
        module_name = '%s.%s' % (module, name)
        try:
            m = getattr(self.loadModule(module_name), name)
            (section, options) = m.config
            self.register.send(section, options = options)
        except:
            log.error("Failed loading config for %s" % name)

    def loadModule(self, name):
        try:
            m = __import__(name)
            splitted = name.split('.')
            for sub in splitted[1:-1]:
                m = getattr(m, sub)
            return m
        except:
            raise

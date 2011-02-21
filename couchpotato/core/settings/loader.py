from blinker import signal
from couchpotato.core.logger import CPLog
import glob
import os

log = CPLog(__name__)

class SettingsLoader:

    configs = {}
    sections = {}

    def __init__(self):
        self.settings_register = signal('settings.register')
        self.settings_save = signal('settings.save')

    def load(self, root = ''):

        self.paths = {
            'plugins' : ('couchpotato.core.plugins', os.path.join(root, 'couchpotato', 'core', 'plugins')),
            'providers' : ('couchpotato.core.providers', os.path.join(root, 'couchpotato', 'core', 'providers')),
        }

        for type, tuple in self.paths.iteritems():
            self.addFromDir(tuple[0], tuple[1])

    def run(self):
        did_save = 0

        for module, plugin_name in self.configs.iteritems():
            did_save += self.loadConfig(module, plugin_name, save = False)

        if did_save:
            self.settings_save.send()

    def addFromDir(self, module, dir):

        for file in glob.glob(os.path.join(dir, '*')):
            name = os.path.basename(file)
            if os.path.isdir(os.path.join(dir, name)):
                self.addConfig(module, name)

    def loadConfig(self, module, name, save = True):
        module_name = '%s.%s' % (module, name)
        try:
            m = getattr(self.loadModule(module_name), name)

            for section in m.config:
                self.addSection(section['name'], section)
                options = {}
                for key, option in section['options'].iteritems():
                    options[key] = option['default']
                self.settings_register.send(section['name'], options = options, save = save)

            return True
        except Exception, e:
            log.error("Failed loading config for %s: %s" % (name, e))
            return False

    def addConfig(self, module, name):
        self.configs[module] = name

    def loadModule(self, name):
        try:
            m = __import__(name)
            splitted = name.split('.')
            for sub in splitted[1:-1]:
                m = getattr(m, sub)
            return m
        except:
            raise

    def addSection(self, section_name, options):
        self.sections[section_name] = options

    def getSections(self):
        return self.sections

settings_loader = SettingsLoader()

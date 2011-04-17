from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
import glob
import os

log = CPLog(__name__)

class Loader:

    plugins = {}
    providers = {}

    modules = {}

    def preload(self, root = ''):

        core = os.path.join(root, 'couchpotato', 'core')
        providers = os.path.join(root, 'couchpotato', 'core', 'providers')

        self.paths = {
            'core' : (0, 'couchpotato.core._base', os.path.join(core, '_base')),
            'plugin' : (1, 'couchpotato.core.plugins', os.path.join(core, 'plugins')),
            'notifications' : (20, 'couchpotato.core.notifications', os.path.join(core, 'notifications')),
            'downloaders' : (20, 'couchpotato.core.downloaders', os.path.join(core, 'downloaders')),
            'movie_provider' : (20, 'couchpotato.core.providers.movie', os.path.join(providers, 'movie')),
            'nzb_provider' : (20, 'couchpotato.core.providers.nzb', os.path.join(providers, 'nzb')),
            'torrent_provider' : (20, 'couchpotato.core.providers.torrent', os.path.join(providers, 'torrent')),
            'trailer_provider' : (20, 'couchpotato.core.providers.trailer', os.path.join(providers, 'trailer')),
            'subtitle_provider' : (20, 'couchpotato.core.providers.subtitle', os.path.join(providers, 'subtitle')),
        }

        for type, tuple in self.paths.iteritems():
            priority, module, dir = tuple
            self.addFromDir(type, priority, module, dir)

    def run(self):
        did_save = 0

        for priority in self.modules:
            for module_name, plugin in sorted(self.modules[priority].iteritems()):
                # Load module
                try:
                    m = getattr(self.loadModule(module_name), plugin.get('name'))

                    log.info("Loading %s: %s" % (plugin['type'], plugin['name']))

                    # Save default settings for plugin/provider
                    did_save += self.loadSettings(m, module_name, save = False)

                    self.loadPlugins(m, plugin.get('name'))
                except Exception, e:
                    log.error('Can\'t import %s: %s' % (module_name, e))

        if did_save:
            fireEvent('settings.save')

    def addFromDir(self, type, priority, module, dir):

        for file in glob.glob(os.path.join(dir, '*')):
            name = os.path.basename(file)
            if os.path.isdir(os.path.join(dir, name)):
                module_name = '%s.%s' % (module, name)
                self.addModule(priority, type, module_name, name)

    def loadSettings(self, module, name, save = True):
        try:
            for section in module.config:
                fireEvent('settings.options', section['name'], section)
                options = {}
                for group in section['groups']:
                    for option in group['options']:
                        options[option['name']] = option.get('default', '')
                fireEvent('settings.register', section_name = section['name'], options = options, save = save)
            return True
        except Exception, e:
            log.debug("Failed loading settings for '%s': %s" % (name, e))
            return False

    def loadPlugins(self, module, name):
        try:
            module.start()
            return True
        except Exception, e:
            log.error("Failed loading plugin '%s': %s" % (name, e))
            return False

    def addModule(self, priority, type, module, name):

        if not self.modules.get(priority):
            self.modules[priority] = {}

        self.modules[priority][module] = {
            'priority': priority,
            'module': module,
            'type': type,
            'name': name,
        }

    def loadModule(self, name):
        try:
            m = __import__(name)
            splitted = name.split('.')
            for sub in splitted[1:-1]:
                m = getattr(m, sub)
            return m
        except:
            raise

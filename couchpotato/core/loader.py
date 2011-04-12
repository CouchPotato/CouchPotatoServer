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
            'plugin' : ('couchpotato.core.plugins', os.path.join(core, 'plugins')),
            'notifications' : ('couchpotato.core.notifications', os.path.join(core, 'notifications')),
            'downloaders' : ('couchpotato.core.downloaders', os.path.join(root, 'couchpotato', 'core', 'downloaders')),
            'movie_provider' : ('couchpotato.core.providers.movie', os.path.join(providers, 'movie')),
            'nzb_provider' : ('couchpotato.core.providers.nzb', os.path.join(providers, 'nzb')),
            'torrent_provider' : ('couchpotato.core.providers.torrent', os.path.join(providers, 'torrent')),
            'trailer_provider' : ('couchpotato.core.providers.trailer', os.path.join(providers, 'trailer')),
            'subtitle_provider' : ('couchpotato.core.providers.subtitle', os.path.join(providers, 'subtitle')),
        }

        for type, tuple in self.paths.iteritems():
            self.addFromDir(type, tuple[0], tuple[1])

    def run(self):
        did_save = 0

        for module_name, plugin in sorted(self.modules.iteritems()):

            # Load module
            try:
                m = getattr(self.loadModule(module_name), plugin.get('name'))

                log.info("Loading %s: %s" % (plugin['type'], plugin['name']))

                # Save default settings for plugin/provider
                did_save += self.loadSettings(m, module_name, save = False)

                self.loadPlugins(m, plugin.get('name'))
            except Exception, e:
                log.error(e)

        if did_save:
            fireEvent('settings.save')

    def addFromDir(self, type, module, dir):

        for file in glob.glob(os.path.join(dir, '*')):
            name = os.path.basename(file)
            if os.path.isdir(os.path.join(dir, name)):
                module_name = '%s.%s' % (module, name)
                self.addModule(type, module_name, name)

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

    def addModule(self, type, module, name):
        self.modules[module] = {
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

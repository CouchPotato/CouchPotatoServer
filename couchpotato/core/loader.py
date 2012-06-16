from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
import glob
import os
import traceback

log = CPLog(__name__)

class Loader(object):

    plugins = {}
    providers = {}

    modules = {}

    def preload(self, root = ''):

        core = os.path.join(root, 'couchpotato', 'core')

        self.paths = {
            'core': (0, 'couchpotato.core._base', os.path.join(core, '_base')),
            'plugin': (1, 'couchpotato.core.plugins', os.path.join(core, 'plugins')),
            'notifications': (20, 'couchpotato.core.notifications', os.path.join(core, 'notifications')),
            'downloaders': (20, 'couchpotato.core.downloaders', os.path.join(core, 'downloaders')),
        }

        # Add providers to loader
        provider_dir = os.path.join(root, 'couchpotato', 'core', 'providers')
        for provider in os.listdir(provider_dir):
            path = os.path.join(provider_dir, provider)
            if os.path.isdir(path):
                self.paths[provider + '_provider'] = (25, 'couchpotato.core.providers.' + provider, path)


        for plugin_type, plugin_tuple in self.paths.iteritems():
            priority, module, dir_name = plugin_tuple
            self.addFromDir(plugin_type, priority, module, dir_name)

    def run(self):
        did_save = 0

        for priority in self.modules:
            for module_name, plugin in sorted(self.modules[priority].iteritems()):
                # Load module
                try:
                    m = getattr(self.loadModule(module_name), plugin.get('name'))

                    log.info('Loading %s: %s', (plugin['type'], plugin['name']))

                    # Save default settings for plugin/provider
                    did_save += self.loadSettings(m, module_name, save = False)

                    self.loadPlugins(m, plugin.get('name'))
                except ImportError as e:
                    # todo:: subclass ImportError for missing requirements.
                    if (e.message.lower().startswith("missing")):
                        log.error(e.message)
                        pass
                    # todo:: this needs to be more descriptive.
                    log.error('Import error, remove the empty folder: %s', plugin.get('module'))
                    log.debug('Can\'t import %s: %s', (module_name, traceback.format_exc()))
                except:
                    log.error('Can\'t import %s: %s', (module_name, traceback.format_exc()))

        if did_save:
            fireEvent('settings.save')

    def addFromDir(self, plugin_type, priority, module, dir_name):

        for cur_file in glob.glob(os.path.join(dir_name, '*')):
            name = os.path.basename(cur_file)
            if os.path.isdir(os.path.join(dir_name, name)):
                module_name = '%s.%s' % (module, name)
                self.addModule(priority, plugin_type, module_name, name)

    def loadSettings(self, module, name, save = True):
        try:
            for section in module.config:
                fireEvent('settings.options', section['name'], section)
                options = {}
                for group in section['groups']:
                    for option in group['options']:
                        options[option['name']] = option
                fireEvent('settings.register', section_name = section['name'], options = options, save = save)
            return True
        except:
            log.debug('Failed loading settings for "%s": %s', (name, traceback.format_exc()))
            return False

    def loadPlugins(self, module, name):
        try:
            klass = module.start()
            klass.registerPlugin()

            if klass and getattr(klass, 'auto_register_static'):
                klass.registerStatic(module.__file__)

            return True
        except Exception, e:
            log.error('Failed loading plugin "%s": %s', (module.__file__, traceback.format_exc()))
            return False

    def addModule(self, priority, plugin_type, module, name):

        if not self.modules.get(priority):
            self.modules[priority] = {}

        self.modules[priority][module] = {
            'priority': priority,
            'module': module,
            'type': plugin_type,
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

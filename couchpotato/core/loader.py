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

    def addPath(self, root, base_path, priority, recursive = False):
        for filename in os.listdir(os.path.join(root, *base_path)):
            path = os.path.join(os.path.join(root, *base_path), filename)
            if os.path.isdir(path) and filename[:2] != '__':
                if u'__init__.py' in os.listdir(path):
                    new_base_path = ''.join(s + '.' for s in base_path) + filename
                    self.paths[new_base_path.replace('.', '_')] = (priority, new_base_path, path)

                if recursive:
                    self.addPath(root, base_path + [filename], priority, recursive = True)

    def preload(self, root = ''):
        core = os.path.join(root, 'couchpotato', 'core')

        self.paths = {
            'core': (0, 'couchpotato.core._base', os.path.join(core, '_base')),
            'plugin': (1, 'couchpotato.core.plugins', os.path.join(core, 'plugins')),
            'notifications': (20, 'couchpotato.core.notifications', os.path.join(core, 'notifications')),
            'downloaders': (20, 'couchpotato.core.downloaders', os.path.join(core, 'downloaders')),
        }

        # Add providers to loader
        self.addPath(root, ['couchpotato', 'core', 'providers'], 25, recursive = False)

        # Add media to loader
        self.addPath(root, ['couchpotato', 'core', 'media'], 25, recursive = True)

        for plugin_type, plugin_tuple in self.paths.iteritems():
            priority, module, dir_name = plugin_tuple
            self.addFromDir(plugin_type, priority, module, dir_name)

    def run(self):
        did_save = 0

        for priority in self.modules:
            for module_name, plugin in sorted(self.modules[priority].iteritems()):
                # Load module
                try:
                    if plugin.get('name')[:2] == '__':
                        continue

                    m = self.loadModule(module_name)
                    if m is None:
                        continue
                    m = getattr(m, plugin.get('name'))

                    log.info('Loading %s: %s', (plugin['type'], plugin['name']))

                    # Save default settings for plugin/provider
                    did_save += self.loadSettings(m, module_name, save = False)

                    self.loadPlugins(m, plugin.get('name'))
                except ImportError as e:
                    # todo:: subclass ImportError for missing requirements.
                    if e.message.lower().startswith("missing"):
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

        # Load dir module
        try:
            m = __import__(module)
            splitted = module.split('.')
            for sub in splitted[1:]:
                m = getattr(m, sub)
        except:
            raise

        for cur_file in glob.glob(os.path.join(dir_name, '*')):
            name = os.path.basename(cur_file)
            if os.path.isdir(os.path.join(dir_name, name)) and name != 'static' and os.path.isfile(os.path.join(cur_file, '__init__.py')):
                module_name = '%s.%s' % (module, name)
                self.addModule(priority, plugin_type, module_name, name)

    def loadSettings(self, module, name, save = True):

        if not hasattr(module, 'config'):
            log.debug('Skip loading settings for plugin %s as it has no config section' % module.__file__)
            return False

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

        if not hasattr(module, 'start'):
            log.debug('Skip startup for plugin %s as it has no start section' % module.__file__)
            return False
        try:
            module.start()
            return True
        except:
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
        except ImportError:
            log.debug('Skip loading module plugin %s: %s', (name, traceback.format_exc()))
            return None
        except:
            raise

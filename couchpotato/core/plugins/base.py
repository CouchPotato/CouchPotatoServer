from couchpotato import addView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.variable import getExt
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
from flask.helpers import send_from_directory
import glob
import os.path
import re

log = CPLog(__name__)


class Plugin(object):

    enabled_option = 'enabled'
    auto_register_static = True

    needs_shutdown = False

    def registerPlugin(self):
        addEvent('app.shutdown', self.doShutdown)

    def conf(self, attr, default = None):
        return Env.setting(attr, self.getName().lower(), default = default)

    def getName(self):
        return self.__class__.__name__

    def registerStatic(self, plugin_file, add_to_head = True):

        # Register plugin path
        self.plugin_path = os.path.dirname(plugin_file)

        # Get plugin_name from PluginName
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.__class__.__name__)
        class_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

        path = 'static/' + class_name + '/'
        addView(path + '<path:file>', self.showStatic, static = True)

        if add_to_head:
            for file in glob.glob(os.path.join(self.plugin_path, 'static', '*')):
                fireEvent('register_%s' % ('script' if getExt(file) in 'js' else 'style'), path + os.path.basename(file))

    def showStatic(self, file = ''):
        dir = os.path.join(self.plugin_path, 'static')
        return send_from_directory(dir, file)

    def createFile(self, path, content):

        self.makeDir(os.path.dirname(path))

        try:
            file = open(path, 'w')
            file.write(content)
            file.close()
        except Exception, e:
            log.error('Unable writing to file "%s": %s' % (path, e))

    def makeDir(self, path):
        try:
            if not os.path.isdir(path):
                os.makedirs(path, Env.getPermission('folder'))
        except Exception, e:
            log.error('Unable to create folder "%s": %s' % (path, e))


    def doShutdown(self):
        self.shuttingDown(True)

    def shuttingDown(self, value = None):
        if value is None:
            return self.needs_shutdown

        self.needs_shutdown = value

    def isDisabled(self):
        return not self.isEnabled()

    def isEnabled(self):
        return self.conf(self.enabled_option) or self.conf(self.enabled_option) == None

from couchpotato import addView
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import getExt
from couchpotato.environment import Env
from flask.helpers import send_from_directory
import glob
import os.path
import re


class Plugin(object):

    def conf(self, attr, default = None):
        return Env.setting(attr, self.getName().lower(), default = default)

    def getName(self):
        return self.__class__.__name__

    def registerStatic(self, plugin_file):

        # Register plugin path
        self.plugin_path = os.path.dirname(plugin_file)

        # Get plugin_name from PluginName
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.__class__.__name__)
        class_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

        path = 'static/' + class_name + '/'
        addView(path + '<path:file>', self.showStatic, static = True)

        for file in glob.glob(os.path.join(self.plugin_path, 'static', '*')):
            fireEvent('register_script' if getExt(file) in 'js' else 'register_style', path + os.path.basename(file))

    def showStatic(self, file = ''):
        dir = os.path.join(self.plugin_path, 'static')
        return send_from_directory(dir, file)

    def isDisabled(self):
        return not self.isEnabled()

    def isEnabled(self):
        return self.conf('enabled') or self.conf('enabled') == None

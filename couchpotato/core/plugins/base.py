from couchpotato.api import addApiView
from couchpotato.environment import Env
from flask.helpers import send_from_directory
import os.path


class Plugin():

    def conf(self, attr):
        return Env.setting(attr, self.getName().lower())

    def getName(self):
        return self.__class__.__name__

    def registerStatic(self, file_path):

        class_name = self.__class__.__name__.lower()
        self.plugin_file = file_path
        path = class_name + '.static/'

        addApiView(path + '<path:file>', self.showStatic, static = True)

        return path

    def showStatic(self, file = ''):

        plugin_dir = os.path.dirname(self.plugin_file)
        dir = os.path.join(plugin_dir, 'static')

        return send_from_directory(dir, file)

    def isDisabled(self):
        return not self.isEnabled()

    def isEnabled(self):
        return self.conf('enabled', True)

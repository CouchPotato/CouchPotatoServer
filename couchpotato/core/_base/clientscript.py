import os

from couchpotato.core.event import addEvent
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env


log = CPLog(__name__)

autoload = 'ClientScript'


class ClientScript(Plugin):

    paths = {
        'style': [
            'style/combined.min.css',
        ],
        'script': [
            'scripts/combined.vendor.min.js',
            'scripts/combined.base.min.js',
            'scripts/combined.plugins.min.js',
        ],
    }

    def __init__(self):
        addEvent('clientscript.get_styles', self.getStyles)
        addEvent('clientscript.get_scripts', self.getScripts)

        self.makeRelative()

    def makeRelative(self):

        for static_type in self.paths:

            updates_paths = []
            for rel_path in self.paths.get(static_type):
                file_path = os.path.join(Env.get('app_dir'), 'couchpotato', 'static', rel_path)
                core_url = 'static/%s?%d' % (rel_path, tryInt(os.path.getmtime(file_path)))

                updates_paths.append(core_url)

            self.paths[static_type] = updates_paths

    def getStyles(self, *args, **kwargs):
        return self.get('style', *args, **kwargs)

    def getScripts(self, *args, **kwargs):
        return self.get('script', *args, **kwargs)

    def get(self, type):
        if type in self.paths:
            return self.paths[type]

        return []

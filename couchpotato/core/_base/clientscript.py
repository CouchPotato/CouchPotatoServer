import os
import re

from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import ss
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from tornado.web import StaticFileHandler


log = CPLog(__name__)

autoload = 'ClientScript'


class ClientScript(Plugin):

    core_static = {
        'style': [
            'style/combined.min.css',
        ],
        'script': [
            'scripts/vendor/mootools.js',
            'scripts/vendor/mootools_more.js',
            'scripts/vendor/form_replacement/form_check.js',
            'scripts/vendor/form_replacement/form_radio.js',
            'scripts/vendor/form_replacement/form_dropdown.js',
            'scripts/vendor/form_replacement/form_selectoption.js',
            'scripts/vendor/Array.stableSort.js',
            'scripts/vendor/history.js',
            'scripts/library/uniform.js',
            'scripts/library/question.js',
            'scripts/library/scrollspy.js',
            'scripts/couchpotato.js',
            'scripts/api.js',
            'scripts/page.js',
            'scripts/block.js',
            'scripts/block/navigation.js',
            'scripts/block/header.js',
            'scripts/block/footer.js',
            'scripts/block/menu.js',
            'scripts/page/home.js',
            'scripts/page/settings.js',
            'scripts/page/about.js',
        ],
    }

    watches = {}

    original_paths = {'style': {}, 'script': {}}
    paths = {'style': {}, 'script': {}}
    comment = {
        'style': '/*** %s:%d ***/\n',
        'script': '// %s:%d\n'
    }

    html = {
        'style': '<link rel="stylesheet" href="%s" type="text/css">',
        'script': '<script type="text/javascript" src="%s"></script>',
    }

    def __init__(self):
        addEvent('register_style', self.registerStyle)
        addEvent('register_script', self.registerScript)

        addEvent('clientscript.get_styles', self.getStyles)
        addEvent('clientscript.get_scripts', self.getScripts)

        addEvent('app.load', self.compile)

        self.addCore()

    def addCore(self):

        for static_type in self.core_static:
            for rel_path in self.core_static.get(static_type):
                file_path = os.path.join(Env.get('app_dir'), 'couchpotato', 'static', rel_path)
                core_url = 'static/%s' % rel_path

                if static_type == 'script':
                    self.registerScript(core_url, file_path, position = 'front')
                else:
                    self.registerStyle(core_url, file_path, position = 'front')

    def compile(self):

        # Create cache dir
        cache = Env.get('cache_dir')
        parent_dir = os.path.join(cache, 'minified')
        self.makeDir(parent_dir)

        Env.get('app').add_handlers(".*$", [(Env.get('web_base') + 'minified/(.*)', StaticFileHandler, {'path': parent_dir})])

        for file_type in ['style', 'script']:
            ext = 'js' if file_type is 'script' else 'css'
            positions = self.original_paths.get(file_type, {})
            for position in positions:
                files = positions.get(position)
                self._compile(file_type, files, position, position + '.' + ext)

    def _compile(self, file_type, paths, position, out):

        cache = Env.get('cache_dir')
        out_name = out
        minified_dir = os.path.join(cache, 'minified')

        data_combined = ''

        new_paths = []
        for x in paths:
            file_path, url_path = x

            f = open(file_path, 'r').read()

            if not Env.get('dev'):
                data = f

                data_combined += self.comment.get(file_type) % (ss(file_path), int(os.path.getmtime(file_path)))
                data_combined += data + '\n\n'
            else:
                new_paths.append(x)

        # Combine all files together with some comments
        if not Env.get('dev'):

            out_path = os.path.join(minified_dir, out_name)
            self.createFile(out_path, data_combined.strip())

            minified_url = 'minified/%s?%s' % (out_name, tryInt(os.path.getmtime(out)))
            new_paths.append((out_path, {'url': minified_url}))

        self.paths[file_type][position] = new_paths

    def getStyles(self, *args, **kwargs):
        return self.get('style', *args, **kwargs)

    def getScripts(self, *args, **kwargs):
        return self.get('script', *args, **kwargs)

    def get(self, type, location = 'head'):
        if type in self.paths and location in self.paths[type]:
            paths = self.paths[type][location]
            return [x[1] for x in paths]

        return []

    def registerStyle(self, api_path, file_path, position = 'head'):
        self.register(api_path, file_path, 'style', position)

    def registerScript(self, api_path, file_path, position = 'head'):
        self.register(api_path, file_path, 'script', position)

    def register(self, api_path, file_path, type, location):

        api_path = '%s?%s' % (api_path, tryInt(os.path.getmtime(file_path)))

        if not self.original_paths[type].get(location):
            self.original_paths[type][location] = []
        self.original_paths[type][location].append((file_path, api_path))

        if not self.paths[type].get(location):
            self.paths[type][location] = []
        self.paths[type][location].append((file_path, api_path))

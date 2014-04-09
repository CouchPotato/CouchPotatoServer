import os
import re
import time

from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import ss
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from scss import Scss
from tornado.web import StaticFileHandler


log = CPLog(__name__)

autoload = 'ClientScript'


class ClientScript(Plugin):

    core_static = {
        'style': [
            'style/main.scss',
            'style/uniform.generic.css',
            'style/uniform.css',
            'style/settings.css',
        ],
        'script': [
            'scripts/library/mootools.js',
            'scripts/library/mootools_more.js',
            'scripts/library/uniform.js',
            'scripts/library/form_replacement/form_check.js',
            'scripts/library/form_replacement/form_radio.js',
            'scripts/library/form_replacement/form_dropdown.js',
            'scripts/library/form_replacement/form_selectoption.js',
            'scripts/library/question.js',
            'scripts/library/scrollspy.js',
            'scripts/library/spin.js',
            'scripts/library/Array.stableSort.js',
            'scripts/library/async.js',
            'scripts/couchpotato.js',
            'scripts/api.js',
            'scripts/library/history.js',
            'scripts/page.js',
            'scripts/block.js',
            'scripts/block/navigation.js',
            'scripts/block/footer.js',
            'scripts/block/menu.js',
            'scripts/page/home.js',
            'scripts/page/settings.js',
            'scripts/page/about.js',
        ],
    }

    watcher = None

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

        addEvent('app.load', self.livereload, priority = 1)
        addEvent('app.load', self.compile)

        self.addCore()

    def livereload(self):

        if Env.get('dev'):
            from livereload import Server
            from livereload.watcher import Watcher

            self.livereload_server = Server()
            self.livereload_server.watch('%s/minified/*.css' % Env.get('cache_dir'))
            self.livereload_server.watch('%s/*.css' % os.path.join(Env.get('app_dir'), 'couchpotato', 'static', 'style'))

            self.watcher = Watcher()
            fireEvent('schedule.interval', 'livereload.watcher', self.watcher.examine, seconds = .5)

            self.livereload_server.serve(port = 35729)

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
            positions = self.paths.get(file_type, {})
            for position in positions:
                files = positions.get(position)
                self._compile(file_type, files, position, position + '.' + ext)

    def _compile(self, file_type, paths, position, out):

        cache = Env.get('cache_dir')
        out_name = out
        minified_dir = os.path.join(cache, 'minified')

        data_combined = ''

        raw = []
        for file_path in paths:

            f = open(file_path, 'r').read()

            # Compile scss
            if file_path[-5:] == '.scss':

                # Compile to css
                compiler = Scss(live_errors = True, search_paths = [os.path.dirname(file_path)])
                f = compiler.compile(f)

                # Reload watcher
                if Env.get('dev'):
                    self.watcher.watch(file_path, self.compile)

                    url_path = paths[file_path].get('original_url')
                    compiled_file_name = position + '_%s.css' % url_path.replace('/', '_').split('.scss')[0]
                    compiled_file_path = os.path.join(minified_dir, compiled_file_name)
                    self.createFile(compiled_file_path, f.strip())

                    # Remove scss path
                    paths[file_path]['url'] = 'minified/%s?%s' % (compiled_file_name, tryInt(time.time()))

            if not Env.get('dev'):

                if file_type == 'script':
                    data = f
                else:
                    data = self.prefix(f)
                    data = data.replace('../images/', '../static/images/')
                    data = data.replace('../fonts/', '../static/fonts/')
                    data = data.replace('../../static/', '../static/')  # Replace inside plugins

                data_combined += self.comment.get(file_type) % (ss(file_path), int(os.path.getmtime(file_path)))
                data_combined += data + '\n\n'

                del paths[file_path]

        # Combine all files together with some comments
        if not Env.get('dev'):

            self.createFile(os.path.join(minified_dir, out_name), data_combined.strip())

            minified_url = 'minified/%s?%s' % (out_name, tryInt(os.path.getmtime(out)))
            self.minified[file_type][position].append(minified_url)

    def getStyles(self, *args, **kwargs):
        return self.get('style', *args, **kwargs)

    def getScripts(self, *args, **kwargs):
        return self.get('script', *args, **kwargs)

    def get(self, type, location = 'head'):
        paths = self.paths[type][location]
        return [paths[x].get('url', paths[x].get('original_url')) for x in paths]

    def registerStyle(self, api_path, file_path, position = 'head'):
        self.register(api_path, file_path, 'style', position)

    def registerScript(self, api_path, file_path, position = 'head'):
        self.register(api_path, file_path, 'script', position)

    def register(self, api_path, file_path, type, location):

        api_path = '%s?%s' % (api_path, tryInt(os.path.getmtime(file_path)))

        if not self.paths[type].get(location):
            self.paths[type][location] = {}
        self.paths[type][location][file_path] = {'original_url': api_path}

    prefix_properties = ['border-radius', 'transform', 'transition', 'box-shadow']
    prefix_tags = ['ms', 'moz', 'webkit']

    def prefix(self, data):

        trimmed_data = re.sub('(\t|\n|\r)+', '', data)

        new_data = ''
        colon_split = trimmed_data.split(';')
        for splt in colon_split:
            curl_split = splt.strip().split('{')
            for curly in curl_split:
                curly = curly.strip()
                for prop in self.prefix_properties:
                    if curly[:len(prop) + 1] == prop + ':':
                        for tag in self.prefix_tags:
                            new_data += ' -%s-%s; ' % (tag, curly)

                new_data += curly + (' { ' if len(curl_split) > 1 else ' ')

            new_data += '; '

        new_data = new_data.replace('{ ;', '; ').replace('} ;', '} ')

        return new_data

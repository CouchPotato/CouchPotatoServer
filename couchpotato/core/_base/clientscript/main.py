from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import ss
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from minify.cssmin import cssmin
from minify.jsmin import jsmin
from tornado.web import StaticFileHandler
import os
import re
import traceback

log = CPLog(__name__)


class ClientScript(Plugin):

    core_static = {
        'style': [
            'style/main.css',
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
            'scripts/page/wanted.js',
            'scripts/page/settings.js',
            'scripts/page/about.js',
            'scripts/page/manage.js',
            'scripts/misc/downloaders.js',
        ],
    }


    urls = {'style': {}, 'script': {}}
    minified = {'style': {}, 'script': {}}
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

        if not Env.get('dev'):
            addEvent('app.load', self.minify)

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


    def minify(self):

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
                self._minify(file_type, files, position, position + '.' + ext)

    def _minify(self, file_type, files, position, out):

        cache = Env.get('cache_dir')
        out_name = out
        out = os.path.join(cache, 'minified', out_name)

        raw = []
        for file_path in files:
            f = open(file_path, 'r').read()

            if file_type == 'script':
                data = jsmin(f)
            else:
                data = self.prefix(f)
                data = cssmin(data)
                data = data.replace('../images/', '../static/images/')
                data = data.replace('../fonts/', '../static/fonts/')
                data = data.replace('../../static/', '../static/') # Replace inside plugins

            raw.append({'file': file_path, 'date': int(os.path.getmtime(file_path)), 'data': data})

        # Combine all files together with some comments
        data = ''
        for r in raw:
            data += self.comment.get(file_type) % (ss(r.get('file')), r.get('date'))
            data += r.get('data') + '\n\n'

        self.createFile(out, data.strip())

        if not self.minified.get(file_type):
            self.minified[file_type] = {}
        if not self.minified[file_type].get(position):
            self.minified[file_type][position] = []

        minified_url = 'minified/%s?%s' % (out_name, tryInt(os.path.getmtime(out)))
        self.minified[file_type][position].append(minified_url)

    def getStyles(self, *args, **kwargs):
        return self.get('style', *args, **kwargs)

    def getScripts(self, *args, **kwargs):
        return self.get('script', *args, **kwargs)

    def get(self, type, as_html = False, location = 'head'):

        data = '' if as_html else []

        try:
            try:
                if not Env.get('dev'):
                    return self.minified[type][location]
            except:
                pass

            return self.urls[type][location]
        except:
            log.error('Error getting minified %s, %s: %s', (type, location, traceback.format_exc()))

        return data

    def registerStyle(self, api_path, file_path, position = 'head'):
        self.register(api_path, file_path, 'style', position)

    def registerScript(self, api_path, file_path, position = 'head'):
        self.register(api_path, file_path, 'script', position)

    def register(self, api_path, file_path, type, location):

        api_path = '%s?%s' % (api_path, tryInt(os.path.getmtime(file_path)))

        if not self.urls[type].get(location):
            self.urls[type][location] = []
        self.urls[type][location].append(api_path)

        if not self.paths[type].get(location):
            self.paths[type][location] = []
        self.paths[type][location].append(file_path)

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

from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class ClientScript(Plugin):

    urls = {
        'style': {},
        'script': {},
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

    def getStyles(self, *args, **kwargs):
        return self.get('style', *args, **kwargs)

    def getScripts(self, *args, **kwargs):
        return self.get('script', *args, **kwargs)

    def get(self, type, as_html = False, location = 'head'):

        data = '' if as_html else []

        try:
            return self.urls[type][location]
        except Exception, e:
            log.error(e)

        return data

    def registerStyle(self, path, position = 'head'):
        self.register(path, 'style', position)

    def registerScript(self, path, position = 'head'):
        self.register(path, 'script', position)

    def register(self, file, type, location):

        if not self.urls[type].get(location):
            self.urls[type][location] = []

        filePath = file
        self.urls[type][location].append(filePath)

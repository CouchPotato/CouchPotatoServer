from couchpotato.api import addApiView
from couchpotato.core.helpers.request import jsonified, getParam
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env


class Logging(Plugin):

    def __init__(self):
        addApiView('logging.get', self.get)

    def get(self):

        nr = int(getParam('nr', 0))
        path = '%s%s' % (Env.get('log_path'), '.%s' % nr if nr > 0 else '')

        # Reverse
        f = open(path, 'r')
        lines = []
        for line in f.readlines():
            lines.insert(0, line)

        log = ''
        for line in lines:
            log += line

        return jsonified({
            'success': True,
            'log': log,
        })

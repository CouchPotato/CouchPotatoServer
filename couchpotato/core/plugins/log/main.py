from couchpotato.api import addApiView
from couchpotato.core.helpers.request import jsonified, getParam
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
import os
import traceback

log = CPLog(__name__)


class Logging(Plugin):

    def __init__(self):
        addApiView('logging.get', self.get)
        addApiView('logging.clear', self.clear)

    def get(self):

        nr = int(getParam('nr', 0))

        total = 1
        for x in range(0, 50):
            path = '%s%s' % (Env.get('log_path'), '.%s' % x if x > 0 else '')

            # Set current path
            if x is nr:
                current_path = path

            # Check see if the log exists
            if not os.path.isfile(path):
                total = x
                break

        # Reverse
        f = open(current_path, 'r')
        lines = []
        for line in f.readlines():
            lines.insert(0, line)

        log = ''
        for line in lines:
            log += line

        return jsonified({
            'success': True,
            'log': log,
            'total': total,
        })

    def clear(self):

        for x in range(0, 50):
            path = '%s%s' % (Env.get('log_path'), '.%s' % x if x > 0 else '')

            try:
                os.remove(path)
            except:
                log.error('Couldn\'t delete file "%s": %s', (path, traceback.format_exc()))

            if not os.path.isfile(path):
                break

        return jsonified({
            'success': True
        })

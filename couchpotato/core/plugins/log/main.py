from couchpotato.api import addApiView
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.request import jsonified, getParam, getParams
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
import os
import traceback

log = CPLog(__name__)


class Logging(Plugin):

    def __init__(self):
        addApiView('logging.get', self.get, docs = {
            'desc': 'Get the full log file by number',
            'params': {
                'nr': {'desc': 'Number of the log to get.'}
            },
            'return': {'type': 'object', 'example': """{
    'success': True,
    'log': string, //Log file
    'total': int, //Total log files available
}"""}
        })
        addApiView('logging.partial', self.partial, docs = {
            'desc': 'Get a partial log',
            'params': {
                'type': {'desc': 'Type of log', 'type': 'string: all(default), error, info, debug'},
                'lines': {'desc': 'Number of lines. Last to first. Default 30'},
            },
            'return': {'type': 'object', 'example': """{
    'success': True,
    'log': string, //Log file
}"""}
        })
        addApiView('logging.clear', self.clear, docs = {
            'desc': 'Remove all the log files'
        })
        addApiView('logging.log', self.log, docs = {
            'desc': 'Log errors',
            'params': {
                'type': {'desc': 'Type of logging, default "error"'},
                '**kwargs': {'type':'object', 'desc': 'All other params will be printed in the log string.'},
            }
        })

    def get(self):

        nr = int(getParam('nr', 0))
        current_path = None

        total = 1
        for x in range(0, 50):

            path = '%s%s' % (Env.get('log_path'), '.%s' % x if x > 0 else '')

            # Check see if the log exists
            if not os.path.isfile(path):
                total = x - 1
                break

            # Set current path
            if x is nr:
                current_path = path

        log = ''
        if current_path:
            f = open(current_path, 'r')
            log = f.read()

        return jsonified({
            'success': True,
            'log': toUnicode(log),
            'total': total,
        })

    def partial(self):

        log_type = getParam('type', 'all')
        total_lines = tryInt(getParam('lines', 30))

        log_lines = []

        for x in range(0, 50):

            path = '%s%s' % (Env.get('log_path'), '.%s' % x if x > 0 else '')

            # Check see if the log exists
            if not os.path.isfile(path):
                break

            reversed_lines = []
            f = open(path, 'r')
            reversed_lines = toUnicode(f.read()).split('[0m\n')
            reversed_lines.reverse()

            brk = False
            for line in reversed_lines:

                if log_type == 'all' or '%s ' % log_type.upper() in line:
                    log_lines.append(line)

                if len(log_lines) >= total_lines:
                    brk = True
                    break

            if brk:
                break

        log_lines.reverse()
        return jsonified({
            'success': True,
            'log': '[0m\n'.join(log_lines),
        })

    def clear(self):

        for x in range(0, 50):
            path = '%s%s' % (Env.get('log_path'), '.%s' % x if x > 0 else '')

            if not os.path.isfile(path):
                break

            try:

                # Create empty file for current logging
                if x is 0:
                    self.createFile(path, '')
                else:
                    os.remove(path)

            except:
                log.error('Couldn\'t delete file "%s": %s', (path, traceback.format_exc()))

        return jsonified({
            'success': True
        })

    def log(self):

        params = getParams()

        try:
            log_message = 'API log: %s' % params
            try:
                getattr(log, params.get('type', 'error'))(log_message)
            except:
                log.error(log_message)
        except:
            log.error('Couldn\'t log via API: %s', params)


        return jsonified({
            'success': True
        })

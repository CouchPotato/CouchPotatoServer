import os
import re
import traceback

from couchpotato.api import addApiView
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import tryInt, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env


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
    'log': [{
        'time': '03-12 09:12:59',
        'type': 'INFO',
        'message': 'Log message'
    }, ..], //Log file
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
    'log': [{
        'time': '03-12 09:12:59',
        'type': 'INFO',
        'message': 'Log message'
    }, ..]
}"""}
        })
        addApiView('logging.clear', self.clear, docs = {
            'desc': 'Remove all the log files'
        })
        addApiView('logging.log', self.log, docs = {
            'desc': 'Log errors',
            'params': {
                'type': {'desc': 'Type of logging, default "error"'},
                '**kwargs': {'type': 'object', 'desc': 'All other params will be printed in the log string.'},
            }
        })

    def get(self, nr = 0, **kwargs):

        nr = tryInt(nr)
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

        log_content = ''
        if current_path:
            f = open(current_path, 'r')
            log_content = f.read()
        logs = self.toList(log_content)

        return {
            'success': True,
            'log': logs,
            'total': total,
        }

    def partial(self, type = 'all', lines = 30, offset = 0, **kwargs):

        total_lines = tryInt(lines)
        offset = tryInt(offset)

        log_lines = []

        for x in range(0, 50):

            path = '%s%s' % (Env.get('log_path'), '.%s' % x if x > 0 else '')

            # Check see if the log exists
            if not os.path.isfile(path):
                break

            f = open(path, 'r')
            log_content = toUnicode(f.read())
            raw_lines = self.toList(log_content)
            raw_lines.reverse()

            brk = False
            for line in raw_lines:

                if type == 'all' or line.get('type') == type.upper():
                    log_lines.append(line)

                if len(log_lines) >= (total_lines + offset):
                    brk = True
                    break

            if brk:
                break

        log_lines = log_lines[offset:]
        log_lines.reverse()

        return {
            'success': True,
            'log': log_lines,
        }

    def toList(self, log_content = ''):

        logs_raw = toUnicode(log_content).split('[0m\n')

        logs = []
        for log in logs_raw:
            split = splitString(log, '\x1b')
            if split:
                try:
                    date, time, log_type = splitString(split[0], ' ')
                    timestamp = '%s %s' % (date, time)
                except:
                    timestamp = 'UNKNOWN'
                    log_type = 'UNKNOWN'

                message = ''.join(split[1]) if len(split) > 1 else split[0]
                message = re.sub('\[\d+m\[', '[', message)

                logs.append({
                    'time': timestamp,
                    'type': log_type,
                    'message': message
                })

        return logs

    def clear(self, **kwargs):

        for x in range(0, 50):
            path = '%s%s' % (Env.get('log_path'), '.%s' % x if x > 0 else '')

            if not os.path.isfile(path):
                continue

            try:

                # Create empty file for current logging
                if x is 0:
                    self.createFile(path, '')
                else:
                    os.remove(path)

            except:
                log.error('Couldn\'t delete file "%s": %s', (path, traceback.format_exc()))

        return {
            'success': True
        }

    def log(self, type = 'error', **kwargs):

        try:
            log_message = 'API log: %s' % kwargs
            try:
                getattr(log, type)(log_message)
            except:
                log.error(log_message)
        except:
            log.error('Couldn\'t log via API: %s', kwargs)

        return {
            'success': True
        }

from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from flask import request
import os


log = CPLog(__name__)

class Core(Plugin):

    def __init__(self):
        addApiView('app.shutdown', self.shutdown)
        addApiView('app.restart', self.restart)

        self.removeRestartFile()

    def shutdown(self):
        self.initShutdown()
        return 'shutdown'

    def restart(self):
        self.initShutdown(restart = True)
        return 'restarting'

    def initShutdown(self, restart = False):

        fireEvent('app.shutdown')

        if restart:
            self.writeRestartFile()

        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()

    def removeRestartFile(self):
        try:
            os.remove(self.restartFilePath())
        except:
            pass

    def writeRestartFile(self):
        try:
            with open(self.restartFilePath(), 'w') as f:
                f.write('This is the most suckiest way to register if CP is restarted. Ever...')
        except Exception, e:
            log.error('Could not write shutdown file: %s' % e)

    def restartFilePath(self):
        return os.path.join(Env.get('data_dir'), 'restart')

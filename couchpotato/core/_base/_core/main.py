from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from flask import request
import os
import time


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

        while 1:
            still_running = fireEvent('plugin.running')

            brk = True
            for running in still_running:
                if running > 0:
                    brk = False

            if brk: break

            time.sleep(1)


        if restart:
            self.createFile(self.restartFilePath(), 'This is the most suckiest way to register if CP is restarted. Ever...')

        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            log.error('Failed shutting down the server')
        func()

    def removeRestartFile(self):
        try:
            os.remove(self.restartFilePath())
        except:
            pass

    def restartFilePath(self):
        return os.path.join(Env.get('data_dir'), 'restart')

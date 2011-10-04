from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from flask import request
import os
import time
import webbrowser


log = CPLog(__name__)

class Core(Plugin):

    def __init__(self):
        addApiView('app.shutdown', self.shutdown)
        addApiView('app.restart', self.restart)

        addEvent('app.load', self.launchBrowser, priority = 100)

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
                if len(running) > 0:
                    log.info('Waiting on plugins to finish: %s' % running)
                    brk = False

            if brk: break

            time.sleep(1)

        if restart:
            self.createFile(self.restartFilePath(), 'This is the most suckiest way to register if CP is restarted. Ever...')

        try:
            request.environ.get('werkzeug.server.shutdown')()
        except:
            log.error('Failed shutting down the server')

    def removeRestartFile(self):
        try:
            os.remove(self.restartFilePath())
        except:
            pass

    def restartFilePath(self):
        return os.path.join(Env.get('app_dir'), 'restart')

    def launchBrowser(self):

        if Env.setting('launch_browser'):
            log.info('Launching browser')

            host = Env.setting('host')
            if host == '0.0.0.0':
                host = 'localhost'
            port = Env.setting('port')

            url = '%s:%d' % (cleanHost(host).rstrip('/'), int(port))
            try:
                webbrowser.open(url, 2, 1)
            except:
                try:
                    webbrowser.open(url, 1, 1)
                except:
                    log.error('Could not launch a browser.')

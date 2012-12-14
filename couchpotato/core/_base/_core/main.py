from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.request import jsonified
from couchpotato.core.helpers.variable import cleanHost, md5
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from tornado.ioloop import IOLoop
from uuid import uuid4
import os
import platform
import signal
import time
import traceback
import webbrowser

log = CPLog(__name__)


class Core(Plugin):

    ignore_restart = [
        'Core.restart', 'Core.shutdown',
        'Updater.check', 'Updater.autoUpdate',
    ]
    shutdown_started = False

    def __init__(self):
        addApiView('app.shutdown', self.shutdown, docs = {
            'desc': 'Shutdown the app.',
            'return': {'type': 'string: shutdown'}
        })
        addApiView('app.restart', self.restart, docs = {
            'desc': 'Restart the app.',
            'return': {'type': 'string: restart'}
        })
        addApiView('app.available', self.available, docs = {
            'desc': 'Check if app available.'
        })
        addApiView('app.version', self.versionView, docs = {
            'desc': 'Get version.'
        })

        addEvent('app.shutdown', self.shutdown)
        addEvent('app.restart', self.restart)
        addEvent('app.load', self.launchBrowser, priority = 1)
        addEvent('app.base_url', self.createBaseUrl)
        addEvent('app.api_url', self.createApiUrl)
        addEvent('app.version', self.version)
        addEvent('app.load', self.checkDataDir)

        addEvent('setting.save.core.password', self.md5Password)
        addEvent('setting.save.core.api_key', self.checkApikey)

        # Make sure we can close-down with ctrl+c properly
        self.signalHandler()

    def md5Password(self, value):
        return md5(value.encode(Env.get('encoding'))) if value else ''

    def checkApikey(self, value):
        return value if value and len(value) > 3 else uuid4().hex

    def checkDataDir(self):
        if Env.get('app_dir') in Env.get('data_dir'):
            log.error('You should NOT use your CouchPotato directory to save your settings in. Files will get overwritten or be deleted.')

        return True

    def available(self):
        return jsonified({
            'success': True
        })

    def shutdown(self):
        if self.shutdown_started:
            return False

        def shutdown():
            self.initShutdown()
        IOLoop.instance().add_callback(shutdown)

        return 'shutdown'

    def restart(self):
        if self.shutdown_started:
            return False

        def restart():
            self.initShutdown(restart = True)
        IOLoop.instance().add_callback(restart)

        return 'restarting'

    def initShutdown(self, restart = False):
        if self.shutdown_started:
            log.info('Already shutting down')
            return

        log.info('Shutting down' if not restart else 'Restarting')

        self.shutdown_started = True

        fireEvent('app.do_shutdown')
        log.debug('Every plugin got shutdown event')

        loop = True
        starttime = time.time()
        while loop:
            log.debug('Asking who is running')
            still_running = fireEvent('plugin.running', merge = True)
            log.debug('Still running: %s', still_running)

            if len(still_running) == 0:
                break
            elif starttime < time.time() - 30: # Always force break after 30s wait
                break

            running = list(set(still_running) - set(self.ignore_restart))
            if len(running) > 0:
                log.info('Waiting on plugins to finish: %s', running)
            else:
                loop = False

            time.sleep(1)

        log.debug('Save to shutdown/restart')

        try:
            IOLoop.instance().stop()
        except RuntimeError:
            pass
        except:
            log.error('Failed shutting down the server: %s', traceback.format_exc())

        fireEvent('app.after_shutdown', restart = restart)

    def launchBrowser(self):

        if Env.setting('launch_browser'):
            log.info('Launching browser')

            url = self.createBaseUrl()
            try:
                webbrowser.open(url, 2, 1)
            except:
                try:
                    webbrowser.open(url, 1, 1)
                except:
                    log.error('Could not launch a browser.')

    def createBaseUrl(self):
        host = Env.setting('host')
        if host == '0.0.0.0':
            host = 'localhost'
        port = Env.setting('port')

        return '%s:%d%s' % (cleanHost(host).rstrip('/'), int(port), '/' + Env.setting('url_base').lstrip('/') if Env.setting('url_base') else '')

    def createApiUrl(self):
        return '%s/api/%s' % (self.createBaseUrl(), Env.setting('api_key'))

    def version(self):
        ver = fireEvent('updater.info', single = True)

        if os.name == 'nt': platf = 'windows'
        elif 'Darwin' in platform.platform(): platf = 'osx'
        else: platf = 'linux'

        return '%s - %s-%s - v2' % (platf, ver.get('version')['type'], ver.get('version')['hash'])

    def versionView(self):
        return jsonified({
            'version': self.version()
        })

    def signalHandler(self):

        def signal_handler(signal, frame):
            fireEvent('app.do_shutdown')

        signal.signal(signal.SIGINT, signal_handler)

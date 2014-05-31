from uuid import uuid4
import os
import platform
import signal
import time
import traceback
import webbrowser

from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.variable import cleanHost, md5
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from tornado.ioloop import IOLoop


log = CPLog(__name__)

autoload = 'Core'


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
        addEvent('app.load', self.cleanUpFolders)

        addEvent('setting.save.core.password', self.md5Password)
        addEvent('setting.save.core.api_key', self.checkApikey)

        # Make sure we can close-down with ctrl+c properly
        if not Env.get('desktop'):
            self.signalHandler()

        # Set default urlopen timeout
        import socket
        socket.setdefaulttimeout(30)

    def md5Password(self, value):
        return md5(value) if value else ''

    def checkApikey(self, value):
        return value if value and len(value) > 3 else uuid4().hex

    def checkDataDir(self):
        if Env.get('app_dir') in Env.get('data_dir'):
            log.error('You should NOT use your CouchPotato directory to save your settings in. Files will get overwritten or be deleted.')

        return True

    def cleanUpFolders(self):
        self.deleteEmptyFolder(Env.get('app_dir'), show_error = False)

    def available(self, **kwargs):
        return {
            'success': True
        }

    def shutdown(self, **kwargs):
        if self.shutdown_started:
            return False

        def shutdown():
            self.initShutdown()

        if IOLoop.current()._closing:
            shutdown()
        else:
            IOLoop.current().add_callback(shutdown)

        return 'shutdown'

    def restart(self, **kwargs):
        if self.shutdown_started:
            return False

        def restart():
            self.initShutdown(restart = True)
        IOLoop.current().add_callback(restart)

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
            elif starttime < time.time() - 30:  # Always force break after 30s wait
                break

            running = list(set(still_running) - set(self.ignore_restart))
            if len(running) > 0:
                log.info('Waiting on plugins to finish: %s', running)
            else:
                loop = False

            time.sleep(1)

        log.debug('Safe to shutdown/restart')

        try:
            if not IOLoop.current()._closing:
                IOLoop.current().stop()
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
        if host == '0.0.0.0' or host == '':
            host = 'localhost'
        port = Env.setting('port')

        return '%s:%d%s' % (cleanHost(host).rstrip('/'), int(port), Env.get('web_base'))

    def createApiUrl(self):
        return '%sapi/%s' % (self.createBaseUrl(), Env.setting('api_key'))

    def version(self):
        ver = fireEvent('updater.info', single = True)

        if os.name == 'nt': platf = 'windows'
        elif 'Darwin' in platform.platform(): platf = 'osx'
        else: platf = 'linux'

        return '%s - %s-%s - v2' % (platf, ver.get('version')['type'], ver.get('version')['hash'])

    def versionView(self, **kwargs):
        return {
            'version': self.version()
        }

    def signalHandler(self):
        if Env.get('daemonized'): return

        def signal_handler(*args, **kwargs):
            fireEvent('app.shutdown', single = True)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


config = [{
    'name': 'core',
    'order': 1,
    'groups': [
        {
            'tab': 'general',
            'name': 'basics',
            'description': 'Needs restart before changes take effect.',
            'wizard': True,
            'options': [
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
                {
                    'name': 'port',
                    'default': 5050,
                    'type': 'int',
                    'description': 'The port I should listen to.',
                },
                {
                    'name': 'ssl_cert',
                    'description': 'Path to SSL server.crt',
                    'advanced': True,
                },
                {
                    'name': 'ssl_key',
                    'description': 'Path to SSL server.key',
                    'advanced': True,
                },
                {
                    'name': 'launch_browser',
                    'default': True,
                    'type': 'bool',
                    'description': 'Launch the browser when I start.',
                    'wizard': True,
                },
            ],
        },
        {
            'tab': 'general',
            'name': 'advanced',
            'description': "For those who know what they're doing",
            'advanced': True,
            'options': [
                {
                    'name': 'api_key',
                    'default': uuid4().hex,
                    'readonly': 1,
                    'description': 'Let 3rd party app do stuff. <a target="_self" href="../../docs/">Docs</a>',
                },
                {
                    'name': 'debug',
                    'default': 0,
                    'type': 'bool',
                    'description': 'Enable debugging.',
                },
                {
                    'name': 'development',
                    'default': 0,
                    'type': 'bool',
                    'description': 'Enable this if you\'re developing, and NOT in any other case, thanks.',
                },
                {
                    'name': 'data_dir',
                    'type': 'directory',
                    'description': 'Where cache/logs/etc are stored. Keep empty for defaults.',
                },
                {
                    'name': 'url_base',
                    'default': '',
                    'description': 'When using mod_proxy use this to append the url with this.',
                },
                {
                    'name': 'permission_folder',
                    'default': '0755',
                    'label': 'Folder CHMOD',
                    'description': 'Can be either decimal (493) or octal (leading zero: 0755)',
                },
                {
                    'name': 'permission_file',
                    'default': '0755',
                    'label': 'File CHMOD',
                    'description': 'Same as Folder CHMOD but for files',
                },
            ],
        },
    ],
}]

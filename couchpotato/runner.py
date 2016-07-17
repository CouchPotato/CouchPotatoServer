from logging import handlers
from uuid import uuid4
import locale
import logging
import os.path
import sys
import time
import traceback
import warnings
import re
import tarfile
import shutil

from CodernityDB.database_super_thread_safe import SuperThreadSafeDatabase
from argparse import ArgumentParser
from cache import FileSystemCache
from couchpotato import KeyHandler, LoginHandler, LogoutHandler
from couchpotato.api import NonBlockHandler, ApiHandler
from couchpotato.core.event import fireEventAsync, fireEvent
from couchpotato.core.helpers.encoding import sp
from couchpotato.core.helpers.variable import getDataDir, tryInt, getFreeSpace
import requests
from requests.packages.urllib3 import disable_warnings
from tornado.httpserver import HTTPServer
from tornado.web import Application, StaticFileHandler, RedirectHandler
from couchpotato.core.softchroot import SoftChrootInitError
try: from tornado.netutil import bind_unix_socket
except: pass

def getOptions(args):

    # Options
    parser = ArgumentParser(prog = 'CouchPotato.py')
    parser.add_argument('--data_dir',
                        dest = 'data_dir', help = 'Absolute or ~/ path of the data dir')
    parser.add_argument('--config_file',
                        dest = 'config_file', help = 'Absolute or ~/ path of the settings file (default DATA_DIR/settings.conf)')
    parser.add_argument('--debug', action = 'store_true',
                        dest = 'debug', help = 'Debug mode')
    parser.add_argument('--console_log', action = 'store_true',
                        dest = 'console_log', help = "Log to console")
    parser.add_argument('--quiet', action = 'store_true',
                        dest = 'quiet', help = 'No console logging')
    parser.add_argument('--daemon', action = 'store_true',
                        dest = 'daemon', help = 'Daemonize the app')
    parser.add_argument('--pid_file',
                        dest = 'pid_file', help = 'Path to pidfile needed for daemon')

    options = parser.parse_args(args)

    data_dir = os.path.expanduser(options.data_dir if options.data_dir else getDataDir())

    if not options.config_file:
        options.config_file = os.path.join(data_dir, 'settings.conf')

    if not options.pid_file:
        options.pid_file = os.path.join(data_dir, 'couchpotato.pid')

    options.config_file = os.path.expanduser(options.config_file)
    options.pid_file = os.path.expanduser(options.pid_file)

    return options


# Tornado monkey patch logging..
def _log(status_code, request):

    if status_code < 400:
        return
    else:
        log_method = logging.debug
    request_time = 1000.0 * request.request_time()
    summary = request.method + " " + request.uri + " (" + \
        request.remote_ip + ")"
    log_method("%d %s %.2fms", status_code, summary, request_time)


def runCouchPotato(options, base_path, args, data_dir = None, log_dir = None, Env = None, desktop = None):

    try:
        locale.setlocale(locale.LC_ALL, "")
        encoding = locale.getpreferredencoding()
    except (locale.Error, IOError):
        encoding = None

    # for OSes that are poorly configured I'll just force UTF-8
    if not encoding or encoding in ('ANSI_X3.4-1968', 'US-ASCII', 'ASCII'):
        encoding = 'UTF-8'

    Env.set('encoding', encoding)

    # Do db stuff
    db_path = sp(os.path.join(data_dir, 'database'))
    old_db_path = os.path.join(data_dir, 'couchpotato.db')

    # Remove database folder if both exists
    if os.path.isdir(db_path) and os.path.isfile(old_db_path):
        db = SuperThreadSafeDatabase(db_path)
        db.open()
        db.destroy()

    # Check if database exists
    db = SuperThreadSafeDatabase(db_path)
    db_exists = db.exists()
    if db_exists:

        # Backup before start and cleanup old backups
        backup_path = sp(os.path.join(data_dir, 'db_backup'))
        backup_count = 5
        existing_backups = []
        if not os.path.isdir(backup_path): os.makedirs(backup_path)

        for root, dirs, files in os.walk(backup_path):
            # Only consider files being a direct child of the backup_path
            if root == backup_path:
                for backup_file in sorted(files):
                    ints = re.findall('\d+', backup_file)

                    # Delete non zip files
                    if len(ints) != 1:
                        try: os.remove(os.path.join(root, backup_file))
                        except: pass
                    else:
                        existing_backups.append((int(ints[0]), backup_file))
            else:
                # Delete stray directories.
                shutil.rmtree(root)

        # Remove all but the last 5
        for eb in existing_backups[:-backup_count]:
            os.remove(os.path.join(backup_path, eb[1]))

        # Create new backup
        new_backup = sp(os.path.join(backup_path, '%s.tar.gz' % int(time.time())))
        zipf = tarfile.open(new_backup, 'w:gz')
        for root, dirs, files in os.walk(db_path):
            for zfilename in files:
                zipf.add(os.path.join(root, zfilename), arcname = 'database/%s' % os.path.join(root[len(db_path) + 1:], zfilename))
        zipf.close()

        # Open last
        db.open()

    else:
        db.create()

    # Force creation of cachedir
    log_dir = sp(log_dir)
    cache_dir = sp(os.path.join(data_dir, 'cache'))
    python_cache = sp(os.path.join(cache_dir, 'python'))

    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)
    if not os.path.exists(python_cache):
        os.mkdir(python_cache)

    session = requests.Session()
    session.max_redirects = 5

    # Register environment settings
    Env.set('app_dir', sp(base_path))
    Env.set('data_dir', sp(data_dir))
    Env.set('log_path', sp(os.path.join(log_dir, 'CouchPotato.log')))
    Env.set('db', db)
    Env.set('http_opener', session)
    Env.set('cache_dir', cache_dir)
    Env.set('cache', FileSystemCache(python_cache))
    Env.set('console_log', options.console_log)
    Env.set('quiet', options.quiet)
    Env.set('desktop', desktop)
    Env.set('daemonized', options.daemon)
    Env.set('args', args)
    Env.set('options', options)

    # Determine debug
    debug = options.debug or Env.setting('debug', default = False, type = 'bool')
    Env.set('debug', debug)

    # Development
    development = Env.setting('development', default = False, type = 'bool')
    Env.set('dev', development)

    # Disable logging for some modules
    for logger_name in ['enzyme', 'guessit', 'subliminal', 'apscheduler', 'tornado', 'requests']:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    for logger_name in ['gntp']:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Disable SSL warning
    disable_warnings()

    # Use reloader
    reloader = debug is True and development and not Env.get('desktop') and not options.daemon

    # Logger
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%m-%d %H:%M:%S')
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)
    logging.addLevelName(19, 'INFO')

    # To screen
    if (debug or options.console_log) and not options.quiet and not options.daemon:
        hdlr = logging.StreamHandler(sys.stderr)
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)

    # To file
    hdlr2 = handlers.RotatingFileHandler(Env.get('log_path'), 'a', 500000, 10, encoding = Env.get('encoding'))
    hdlr2.setFormatter(formatter)
    logger.addHandler(hdlr2)

    # Start logging & enable colors
    # noinspection PyUnresolvedReferences
    import color_logs
    from couchpotato.core.logger import CPLog
    log = CPLog(__name__)
    log.debug('Started with options %s', options)

    # Check soft-chroot dir exists:
    try:
        # Load Soft-Chroot
        soft_chroot = Env.get('softchroot')
        soft_chroot_dir = Env.setting('soft_chroot', section = 'core', default = None, type='unicode' )
        soft_chroot.initialize(soft_chroot_dir)
    except SoftChrootInitError as exc:
        log.error(exc)
        return
    except:
        log.error('Unable to check whether SOFT-CHROOT is defined')
        return

    # Check available space
    try:
        total_space, available_space = getFreeSpace(data_dir)
        if available_space < 100:
            log.error('Shutting down as CP needs some space to work. You\'ll get corrupted data otherwise. Only %sMB left', available_space)
            return
    except:
        log.error('Failed getting diskspace: %s', traceback.format_exc())

    def customwarn(message, category, filename, lineno, file = None, line = None):
        log.warning('%s %s %s line:%s', (category, message, filename, lineno))
    warnings.showwarning = customwarn

    # Create app
    from couchpotato import WebHandler
    web_base = ('/' + Env.setting('url_base').lstrip('/') + '/') if Env.setting('url_base') else '/'
    Env.set('web_base', web_base)

    api_key = Env.setting('api_key')
    if not api_key:
        api_key = uuid4().hex
        Env.setting('api_key', value = api_key)

    api_base = r'%sapi/%s/' % (web_base, api_key)
    Env.set('api_base', api_base)

    # Basic config
    host = Env.setting('host', default = '0.0.0.0')
    host6 = Env.setting('host6', default = '::')

    config = {
        'use_reloader': reloader,
        'port': tryInt(Env.setting('port', default = 5050)),
        'host': host if host and len(host) > 0 else '0.0.0.0',
        'host6': host6 if host6 and len(host6) > 0 else '::',
        'ssl_cert': Env.setting('ssl_cert', default = None),
        'ssl_key': Env.setting('ssl_key', default = None),
    }

    # Load the app
    application = Application(
        [],
        log_function = lambda x: None,
        debug = config['use_reloader'],
        gzip = True,
        cookie_secret = api_key,
        login_url = '%slogin/' % web_base,
    )
    Env.set('app', application)

    # Request handlers
    application.add_handlers(".*$", [
        (r'%snonblock/(.*)(/?)' % api_base, NonBlockHandler),

        # API handlers
        (r'%s(.*)(/?)' % api_base, ApiHandler),  # Main API handler
        (r'%sgetkey(/?)' % web_base, KeyHandler),  # Get API key
        (r'%s' % api_base, RedirectHandler, {"url": web_base + 'docs/'}),  # API docs

        # Login handlers
        (r'%slogin(/?)' % web_base, LoginHandler),
        (r'%slogout(/?)' % web_base, LogoutHandler),

        # Catch all webhandlers
        (r'%s(.*)(/?)' % web_base, WebHandler),
        (r'(.*)', WebHandler),
    ])

    # Static paths
    static_path = '%sstatic/' % web_base
    for dir_name in ['fonts', 'images', 'scripts', 'style']:
        application.add_handlers(".*$", [
            ('%s%s/(.*)' % (static_path, dir_name), StaticFileHandler, {'path': sp(os.path.join(base_path, 'couchpotato', 'static', dir_name))})
        ])
    Env.set('static_path', static_path)

    # Load configs & plugins
    loader = Env.get('loader')
    loader.preload(root = sp(base_path))
    loader.run()

    # Fill database with needed stuff
    fireEvent('database.setup')
    if not db_exists:
        fireEvent('app.initialize', in_order = True)
    fireEvent('app.migrate')

    # Go go go!
    from tornado.ioloop import IOLoop
    from tornado.autoreload import add_reload_hook
    loop = IOLoop.current()

    # Reload hook
    def reload_hook():
        fireEvent('app.shutdown')
    add_reload_hook(reload_hook)

    # Some logging and fire load event
    try: log.info('Starting server on port %(port)s', config)
    except: pass
    fireEventAsync('app.load')

    ssl_options = None
    if config['ssl_cert'] and config['ssl_key']:
        ssl_options = {
            'certfile': config['ssl_cert'],
            'keyfile': config['ssl_key'],
        }

    server = HTTPServer(application, no_keep_alive = True, ssl_options = ssl_options)

    try_restart = True
    restart_tries = 5

    while try_restart:
        try:
            if config['host'].startswith('unix:'):
                server.add_socket(bind_unix_socket(config['host'][5:]))
            else:
                server.listen(config['port'], config['host'])

                if Env.setting('ipv6', default = False):
                    try: server.listen(config['port'], config['host6'])
                    except: log.info2('Tried to bind to IPV6 but failed')

            loop.start()
            server.close_all_connections()
            server.stop()
            loop.close(all_fds = True)
        except Exception as e:
            log.error('Failed starting: %s', traceback.format_exc())
            try:
                nr, msg = e
                if nr == 48:
                    log.info('Port (%s) needed for CouchPotato is already in use, try %s more time after few seconds', (config.get('port'), restart_tries))
                    time.sleep(1)
                    restart_tries -= 1

                    if restart_tries > 0:
                        continue
                    else:
                        return
            except ValueError:
                return
            except:
                pass

            raise

        try_restart = False

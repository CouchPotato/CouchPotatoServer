from argparse import ArgumentParser
from cache import FileSystemCache
from couchpotato import KeyHandler, LoginHandler, LogoutHandler
from couchpotato.api import NonBlockHandler, ApiHandler
from couchpotato.core.event import fireEventAsync, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getDataDir, tryInt
from logging import handlers
from tornado.httpserver import HTTPServer
from tornado.web import Application, StaticFileHandler, RedirectHandler
from uuid import uuid4
import locale
import logging
import os.path
import shutil
import sys
import time
import traceback
import warnings

def getOptions(base_path, args):

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
    db_path = toUnicode(os.path.join(data_dir, 'couchpotato.db'))

    # Backup before start and cleanup old databases
    new_backup = toUnicode(os.path.join(data_dir, 'db_backup', str(int(time.time()))))
    if not os.path.isdir(new_backup): os.makedirs(new_backup)

    # Remove older backups, keep backups 3 days or at least 3
    backups = []
    for directory in os.listdir(os.path.dirname(new_backup)):
        backup = toUnicode(os.path.join(os.path.dirname(new_backup), directory))
        if os.path.isdir(backup):
            backups.append(backup)

    latest_backup = tryInt(os.path.basename(sorted(backups)[-1])) if len(backups) > 0 else 0
    if latest_backup < time.time() - 3600:
        # Create path and copy
        src_files = [options.config_file, db_path, db_path + '-shm', db_path + '-wal']
        for src_file in src_files:
            if os.path.isfile(src_file):
                dst_file = toUnicode(os.path.join(new_backup, os.path.basename(src_file)))
                shutil.copyfile(src_file, dst_file)

                # Try and copy stats seperately
                try: shutil.copystat(src_file, dst_file)
                except: pass

    total_backups = len(backups)
    for backup in backups:
        if total_backups > 3:
            if tryInt(os.path.basename(backup)) < time.time() - 259200:
                for the_file in os.listdir(backup):
                    file_path = os.path.join(backup, the_file)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except:
                        raise

                os.rmdir(backup)
                total_backups -= 1


    # Register environment settings
    Env.set('app_dir', toUnicode(base_path))
    Env.set('data_dir', toUnicode(data_dir))
    Env.set('log_path', toUnicode(os.path.join(log_dir, 'CouchPotato.log')))
    Env.set('db_path', toUnicode('sqlite:///' + db_path))
    Env.set('cache_dir', toUnicode(os.path.join(data_dir, 'cache')))
    Env.set('cache', FileSystemCache(toUnicode(os.path.join(Env.get('cache_dir'), 'python'))))
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

    for logger_name in ['gntp', 'migrate']:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

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
    import color_logs
    from couchpotato.core.logger import CPLog
    log = CPLog(__name__)
    log.debug('Started with options %s', options)

    def customwarn(message, category, filename, lineno, file = None, line = None):
        log.warning('%s %s %s line:%s', (category, message, filename, lineno))
    warnings.showwarning = customwarn

    # Check if database exists
    db = Env.get('db_path')
    db_exists = os.path.isfile(toUnicode(db_path))

    # Load migrations
    if db_exists:

        from migrate.versioning.api import version_control, db_version, version, upgrade
        repo = os.path.join(base_path, 'couchpotato', 'core', 'migration')

        latest_db_version = version(repo)
        try:
            current_db_version = db_version(db, repo)
        except:
            version_control(db, repo, version = latest_db_version)
            current_db_version = db_version(db, repo)

        if current_db_version < latest_db_version:
            if development:
                log.error('There is a database migration ready, but you are running development mode, so it won\'t be used. If you see this, you are stupid. Please disable development mode.')
            else:
                log.info('Doing database upgrade. From %d to %d', (current_db_version, latest_db_version))
                upgrade(db, repo)

    # Configure Database
    from couchpotato.core.settings.model import setup
    setup()

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
    # app.debug = development
    config = {
        'use_reloader': reloader,
        'port': tryInt(Env.setting('port', default = 5050)),
        'host': host if host and len(host) > 0 else '0.0.0.0',
        'ssl_cert': Env.setting('ssl_cert', default = None),
        'ssl_key': Env.setting('ssl_key', default = None),
    }


    # Load the app
    application = Application([],
        log_function = lambda x : None,
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
        (r'%s(.*)(/?)' % api_base, ApiHandler), # Main API handler
        (r'%sgetkey(/?)' % web_base, KeyHandler), # Get API key
        (r'%s' % api_base, RedirectHandler, {"url": web_base + 'docs/'}), # API docs

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
             ('%s%s/(.*)' % (static_path, dir_name), StaticFileHandler, {'path': toUnicode(os.path.join(base_path, 'couchpotato', 'static', dir_name))})
        ])
    Env.set('static_path', static_path)


    # Load configs & plugins
    loader = Env.get('loader')
    loader.preload(root = toUnicode(base_path))
    loader.run()


    # Fill database with needed stuff
    if not db_exists:
        fireEvent('app.initialize', in_order = True)


    # Go go go!
    from tornado.ioloop import IOLoop
    loop = IOLoop.current()


    # Some logging and fire load event
    try: log.info('Starting server on port %(port)s', config)
    except: pass
    fireEventAsync('app.load')


    if config['ssl_cert'] and config['ssl_key']:
        server = HTTPServer(application, no_keep_alive = True, ssl_options = {
           "certfile": config['ssl_cert'],
           "keyfile": config['ssl_key'],
        })
    else:
        server = HTTPServer(application, no_keep_alive = True)

    try_restart = True
    restart_tries = 5

    while try_restart:
        try:
            server.listen(config['port'], config['host'])
            loop.start()
        except Exception, e:
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
            except:
                pass

            raise

        try_restart = False

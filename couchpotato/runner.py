from argparse import ArgumentParser
from cloghandler.cloghandler import ConcurrentRotatingFileHandler
from couchpotato import web
from couchpotato.api import api, NonBlockHandler
from couchpotato.core.event import fireEventAsync, fireEvent
from couchpotato.core.helpers.variable import getDataDir, tryInt
from tornado import autoreload
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, FallbackHandler
from tornado.wsgi import WSGIContainer
from werkzeug.contrib.cache import FileSystemCache
import locale
import logging
import os.path
import shutil
import sys
import time
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
    elif status_code < 500:
        log_method = logging.warning
    else:
        log_method = logging.error
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

    # Do db stuff
    db_path = os.path.join(data_dir, 'couchpotato.db')

    # Backup before start and cleanup old databases
    new_backup = os.path.join(data_dir, 'db_backup', str(int(time.time())))

    # Create path and copy
    if not os.path.isdir(new_backup): os.makedirs(new_backup)
    src_files = [options.config_file, db_path, db_path + '-shm', db_path + '-wal']
    for src_file in src_files:
        if os.path.isfile(src_file):
            shutil.copy2(src_file, os.path.join(new_backup, os.path.basename(src_file)))

    # Remove older backups, keep backups 3 days or at least 3
    backups = []
    for directory in os.listdir(os.path.dirname(new_backup)):
        backup = os.path.join(os.path.dirname(new_backup), directory)
        if os.path.isdir(backup):
            backups.append(backup)

    total_backups = len(backups)
    for backup in backups:
        if total_backups > 3:
            if int(os.path.basename(backup)) < time.time() - 259200:
                for src_file in src_files:
                    b_file = os.path.join(backup, os.path.basename(src_file))
                    if os.path.isfile(b_file):
                        os.remove(b_file)
                os.rmdir(backup)
                total_backups -= 1


    # Register environment settings
    Env.set('encoding', encoding)
    Env.set('app_dir', base_path)
    Env.set('data_dir', data_dir)
    Env.set('log_path', os.path.join(log_dir, 'CouchPotato.log'))
    Env.set('db_path', 'sqlite:///' + db_path)
    Env.set('cache_dir', os.path.join(data_dir, 'cache'))
    Env.set('cache', FileSystemCache(os.path.join(Env.get('cache_dir'), 'python')))
    Env.set('console_log', options.console_log)
    Env.set('quiet', options.quiet)
    Env.set('desktop', desktop)
    Env.set('args', args)
    Env.set('options', options)

    # Determine debug
    debug = options.debug or Env.setting('debug', default = False, type = 'bool')
    Env.set('debug', debug)

    # Development
    development = Env.setting('development', default = False, type = 'bool')
    Env.set('dev', development)

    # Disable logging for some modules
    for logger_name in ['enzyme', 'guessit', 'subliminal', 'apscheduler']:
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

    # To screen
    if (debug or options.console_log) and not options.quiet and not options.daemon:
        hdlr = logging.StreamHandler(sys.stderr)
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)

    # To file
    hdlr2 = ConcurrentRotatingFileHandler(Env.get('log_path'), 'a', 500000, 10)
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


    # Load configs & plugins
    loader = Env.get('loader')
    loader.preload(root = base_path)
    loader.run()


    # Load migrations
    initialize = True
    db = Env.get('db_path')
    if os.path.isfile(db_path):
        initialize = False

        from migrate.versioning.api import version_control, db_version, version, upgrade
        repo = os.path.join(base_path, 'couchpotato', 'core', 'migration')

        latest_db_version = version(repo)
        try:
            current_db_version = db_version(db, repo)
        except:
            version_control(db, repo, version = latest_db_version)
            current_db_version = db_version(db, repo)

        if current_db_version < latest_db_version and not debug:
            log.info('Doing database upgrade. From %d to %d', (current_db_version, latest_db_version))
            upgrade(db, repo)

    # Configure Database
    from couchpotato.core.settings.model import setup
    setup()

    if initialize:
        fireEvent('app.initialize', in_order = True)

    # Create app
    from couchpotato import app
    api_key = Env.setting('api_key')
    url_base = '/' + Env.setting('url_base').lstrip('/') if Env.setting('url_base') else ''

    # Basic config
    app.secret_key = api_key
    # app.debug = development
    config = {
        'use_reloader': reloader,
        'host': Env.setting('host', default = '0.0.0.0'),
        'port': tryInt(Env.setting('port', default = 5000))
    }

    # Static path
    app.static_folder = os.path.join(base_path, 'couchpotato', 'static')
    web.add_url_rule('api/%s/static/<path:filename>' % api_key,
                      endpoint = 'static',
                      view_func = app.send_static_file)

    # Register modules
    app.register_blueprint(web, url_prefix = '%s/' % url_base)
    app.register_blueprint(api, url_prefix = '%s/api/%s/' % (url_base, api_key))

    # Some logging and fire load event
    try: log.info('Starting server on port %(port)s', config)
    except: pass
    fireEventAsync('app.load')

    # Go go go!
    web_container = WSGIContainer(app)
    web_container._log = _log
    loop = IOLoop.instance()

    application = Application([
        (r'%s/api/%s/nonblock/(.*)/' % (url_base, api_key), NonBlockHandler),
        (r'.*', FallbackHandler, dict(fallback = web_container)),
    ],
        log_function = lambda x : None,
        debug = config['use_reloader']
    )

    try_restart = True
    restart_tries = 5

    while try_restart:
        try:
            application.listen(config['port'], config['host'], no_keep_alive = True)
            loop.start()
        except Exception, e:
            try:
                nr, msg = e
                if nr == 48:
                    log.info('Already in use, try %s more time after few seconds', restart_tries)
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

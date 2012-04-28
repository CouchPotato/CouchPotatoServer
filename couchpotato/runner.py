from argparse import ArgumentParser
from couchpotato import web
from couchpotato.api import api
from couchpotato.core.event import fireEventAsync, fireEvent
from couchpotato.core.helpers.variable import getDataDir, tryInt
from logging import handlers
from werkzeug.contrib.cache import FileSystemCache
import atexit
import locale
import logging
import os.path
import sys
import time
import warnings

def getOptions(base_path, args):

    data_dir = getDataDir()

    # Options
    parser = ArgumentParser(prog = 'CouchPotato.py')
    parser.add_argument('--config_file', default = os.path.join(data_dir, 'settings.conf'),
                        dest = 'config_file', help = 'Absolute or ~/ path of the settings file (default ./_data/settings.conf)')
    parser.add_argument('--debug', action = 'store_true',
                        dest = 'debug', help = 'Debug mode')
    parser.add_argument('--console_log', action = 'store_true',
                        dest = 'console_log', help = "Log to console")
    parser.add_argument('--quiet', action = 'store_true',
                        dest = 'quiet', help = 'No console logging')
    parser.add_argument('--nogit', action = 'store_true',
                        dest = 'nogit', help = 'No git available')
    parser.add_argument('--daemon', action = 'store_true',
                        dest = 'daemon', help = 'Daemonize the app')
    parser.add_argument('--pid_file', default = os.path.join(data_dir, 'couchpotato.pid'),
                        dest = 'pid_file', help = 'Path to pidfile needed for daemon')

    options = parser.parse_args(args)

    options.config_file = os.path.expanduser(options.config_file)

    return options


def cleanup():
    fireEvent('app.crappy_shutdown', single = True)
    time.sleep(1)


def runCouchPotato(options, base_path, args, data_dir = None, log_dir = None, Env = None, desktop = None):

    try:
        locale.setlocale(locale.LC_ALL, "")
        encoding = locale.getpreferredencoding()
    except (locale.Error, IOError):
        encoding = None

    # for OSes that are poorly configured I'll just force UTF-8
    if not encoding or encoding in ('ANSI_X3.4-1968', 'US-ASCII', 'ASCII'):
        encoding = 'UTF-8'

    # Register environment settings
    Env.set('encoding', encoding)
    Env.set('uses_git', not options.nogit)
    Env.set('app_dir', base_path)
    Env.set('data_dir', data_dir)
    Env.set('log_path', os.path.join(log_dir, 'CouchPotato.log'))
    Env.set('db_path', 'sqlite:///' + os.path.join(data_dir, 'couchpotato.db'))
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
    if not development:
        atexit.register(cleanup)

    # Use reloader
    reloader = debug is True and development and not Env.get('desktop') and not options.daemon

    # Disable server access log
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    # Only run once when debugging
    fire_load = False
    if os.environ.get('WERKZEUG_RUN_MAIN') or not reloader:

        # Logger
        logger = logging.getLogger()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%H:%M:%S')
        level = logging.DEBUG if debug else logging.INFO
        logger.setLevel(level)

        # To screen
        if (debug or options.console_log) and not options.quiet and not options.daemon:
            hdlr = logging.StreamHandler(sys.stderr)
            hdlr.setFormatter(formatter)
            logger.addHandler(hdlr)

        # To file
        hdlr2 = handlers.RotatingFileHandler(Env.get('log_path'), 'a', 500000, 10)
        hdlr2.setFormatter(formatter)
        logger.addHandler(hdlr2)

        # Start logging & enable colors
        import color_logs
        from couchpotato.core.logger import CPLog
        log = CPLog(__name__)
        log.debug('Started with options %s' % options)

        def customwarn(message, category, filename, lineno, file = None, line = None):
            log.warning('%s %s %s line:%s' % (category, message, filename, lineno))
        warnings.showwarning = customwarn


        # Load configs & plugins
        loader = Env.get('loader')
        loader.preload(root = base_path)
        loader.run()


        # Load migrations
        initialize = True
        db = Env.get('db_path')
        if os.path.isfile(db.replace('sqlite:///', '')):
            initialize = False

            from migrate.versioning.api import version_control, db_version, version, upgrade
            repo = os.path.join(base_path, 'couchpotato', 'core', 'migration')
            logging.getLogger('migrate').setLevel(logging.WARNING) # Disable logging for migration

            latest_db_version = version(repo)
            try:
                current_db_version = db_version(db, repo)
            except:
                version_control(db, repo, version = latest_db_version)
                current_db_version = db_version(db, repo)

            if current_db_version < latest_db_version and not debug:
                log.info('Doing database upgrade. From %d to %d' % (current_db_version, latest_db_version))
                upgrade(db, repo)

        # Configure Database
        from couchpotato.core.settings.model import setup
        setup()

        if initialize:
            fireEvent('app.initialize', in_order = True)

        fire_load = True

    # Create app
    from couchpotato import app
    api_key = Env.setting('api_key')
    url_base = '/' + Env.setting('url_base').lstrip('/') if Env.setting('url_base') else ''

    # Basic config
    app.secret_key = api_key
    config = {
        'use_reloader': reloader,
        'host': Env.setting('host', default = '0.0.0.0'),
        'port': tryInt(Env.setting('port', default = 5000))
    }

    # Static path
    app.static_folder = os.path.join(base_path, 'couchpotato', 'static')
    web.add_url_rule('%s/static/<path:filename>' % api_key,
                      endpoint = 'static',
                      view_func = app.send_static_file)

    # Register modules
    app.register_blueprint(web, url_prefix = '%s/' % url_base)
    app.register_blueprint(api, url_prefix = '%s/%s/' % (url_base, api_key))

    # Some logging and fire load event
    try: log.info('Starting server on port %(port)s' % config)
    except: pass
    if fire_load: fireEventAsync('app.load')

    # Go go go!
    try_restart = True
    restart_tries = 5
    while try_restart:
        try:
            app.run(**config)
        except Exception, e:
            try:
                nr, msg = e
                if nr == 48:
                    log.info('Already in use, try %s more time after few seconds' % restart_tries)
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

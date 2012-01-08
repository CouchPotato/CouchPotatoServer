from argparse import ArgumentParser
from couchpotato import web
from couchpotato.api import api
from couchpotato.core.event import fireEventAsync, fireEvent
from couchpotato.core.helpers.variable import getDataDir, tryInt
from daemon import createDaemon
from logging import handlers
from werkzeug.contrib.cache import FileSystemCache
import logging
import os.path
import socket
import sys
import time
import traceback

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
    parser.add_argument('--daemon', action = 'store_true',
                        dest = 'daemonize', help = 'Daemonize the app')
    parser.add_argument('--quiet', action = 'store_true',
                        dest = 'quiet', help = 'No console logging')
    parser.add_argument('--binary_port', default = None,
                        dest = 'binary_port', help = 'Running from binary build')
    parser.add_argument('--nogit', action = 'store_true',
                        dest = 'nogit', help = 'No git available')

    options = parser.parse_args(args)

    options.config_file = os.path.expanduser(options.config_file)

    return options


def runCouchPotato(options, base_path, args, handle = None):

    # Load settings
    from couchpotato.environment import Env
    settings = Env.get('settings')
    settings.setFile(options.config_file)

    if handle:
        handle(Env)

    # Create data dir if needed
    data_dir = os.path.expanduser(Env.setting('data_dir'))
    if data_dir == '':
        data_dir = getDataDir()

    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)

    # Create logging dir
    log_dir = os.path.join(data_dir, 'logs');
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)

    # Daemonize app
    if options.daemonize:
        createDaemon()


    # Register environment settings
    Env.set('uses_git', not options.nogit)
    Env.set('app_dir', base_path)
    Env.set('data_dir', data_dir)
    Env.set('log_path', os.path.join(log_dir, 'CouchPotato.log'))
    Env.set('db_path', 'sqlite:///' + os.path.join(data_dir, 'couchpotato.db'))
    Env.set('cache_dir', os.path.join(data_dir, 'cache'))
    Env.set('cache', FileSystemCache(os.path.join(Env.get('cache_dir'), 'python')))
    Env.set('console_log', options.console_log)
    Env.set('daemonize', options.daemonize)
    Env.set('quiet', options.quiet)
    Env.set('binary_port', options.binary_port)
    Env.set('args', args)
    Env.set('options', options)

    # Determine debug
    debug = options.debug or Env.setting('debug', default = False, type = 'bool')
    Env.set('debug', debug)

    # Disable server access log
    server_log = logging.getLogger('werkzeug')
    server_log.disabled = True

    # Only run once when debugging
    fire_load = False
    if os.environ.get('WERKZEUG_RUN_MAIN') or not debug or options.binary_port:

        # Logger
        logger = logging.getLogger()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%H:%M:%S')
        level = logging.DEBUG if debug else logging.INFO
        logger.setLevel(level)

        # To screen
        if (debug or options.console_log) and not options.daemonize and not options.quiet:
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


        # Load configs & plugins
        loader = Env.get('loader')
        loader.preload(root = base_path)
        loader.run()


        # Load migrations
        from migrate.versioning.api import version_control, db_version, version, upgrade
        db = Env.get('db_path')
        repo = os.path.join(base_path, 'couchpotato', 'core', 'migration')
        logging.getLogger('migrate').setLevel(logging.WARNING) # Disable logging for migration

        latest_db_version = version(repo)

        initialize = True
        try:
            current_db_version = db_version(db, repo)
            initialize = False
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
            fireEvent('app.initialize')

        fire_load = True

    # Create app
    from couchpotato import app
    api_key = Env.setting('api_key')
    url_base = '/' + Env.setting('url_base').lstrip('/') if Env.setting('url_base') else ''
    reloader = debug is True and not options.daemonize and not options.binary_port

    # Basic config
    app.secret_key = api_key
    config = {
        'use_reloader': reloader,
        'host': Env.setting('host', default = '0.0.0.0'),
        'port': tryInt(Env.setting('port', default = 5000))
    }

    # Static path
    web.add_url_rule(url_base + '/static/<path:filename>',
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
    try:
        app.run(**config)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        log.error('Failed starting: %s' % traceback.format_exc())
        raise

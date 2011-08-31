from argparse import ArgumentParser
from couchpotato import web
from couchpotato.api import api
from couchpotato.core.event import fireEventAsync
from daemon import createDaemon
from logging import handlers
from werkzeug.contrib.cache import FileSystemCache
import logging
import os.path
import sys

def getOptions(base_path, args):

    # Options
    parser = ArgumentParser(prog = 'CouchPotato.py')
    parser.add_argument('-c', '--config_file', default = os.path.join(base_path, '_data', 'settings.conf'),
                        dest = 'config_file', help = 'Absolute or ~/ path of the settings file (default ./_data/settings.conf)')
    parser.add_argument('-t', '--test', '--debug', action = 'store_true',
                        dest = 'debug', help = 'Debug mode')
    parser.add_argument('-q', '--quiet', action = 'store_true',
                        dest = 'quiet', help = "Don't log to console")
    parser.add_argument('-d', '--daemon', action = 'store_true',
                        dest = 'daemonize', help = 'Daemonize the app')
    parser.add_argument('-g', '--nogit', action = 'store_true',
                        dest = 'git', help = 'Running from git')

    options = parser.parse_args(args)

    options.config_file = os.path.expanduser(options.config_file)

    return options


def runCouchPotato(options, base_path, args):

    # Load settings
    from couchpotato.environment import Env
    settings = Env.get('settings')
    settings.setFile(options.config_file)

    # Create data dir if needed
    data_dir = os.path.expanduser(Env.setting('data_dir'))
    if data_dir == '':
        data_dir = os.path.join(base_path, '_data')
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
    Env.set('uses_git', not options.git)
    Env.set('app_dir', base_path)
    Env.set('data_dir', data_dir)
    Env.set('log_path', os.path.join(log_dir, 'CouchPotato.log'))
    Env.set('db_path', 'sqlite:///' + os.path.join(data_dir, 'couchpotato.db'))
    Env.set('cache_dir', os.path.join(data_dir, 'cache'))
    Env.set('cache', FileSystemCache(os.path.join(Env.get('cache_dir'), 'python')))
    Env.set('quiet', options.quiet)
    Env.set('daemonize', options.daemonize)
    Env.set('args', args)

    # Determine debug
    debug = options.debug or Env.setting('debug', default = False)
    Env.set('debug', debug)

    # Only run once when debugging
    if os.environ.get('WERKZEUG_RUN_MAIN') or not debug:

        # Logger
        logger = logging.getLogger()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%H:%M:%S')
        level = logging.DEBUG if debug else logging.INFO
        logger.setLevel(level)

        # To screen
        if debug and not options.quiet and not options.daemonize:
            hdlr = logging.StreamHandler(sys.stderr)
            hdlr.setFormatter(formatter)
            logger.addHandler(hdlr)

        # To file
        hdlr2 = handlers.RotatingFileHandler(Env.get('log_path'), 'a', 500000, 10)
        hdlr2.setFormatter(formatter)
        logger.addHandler(hdlr2)

        # Disable server access log
        server_log = logging.getLogger('werkzeug')
        server_log.disabled = True

        # Start logging
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

        fireEventAsync('app.load')

    # Create app
    from couchpotato import app
    api_key = Env.setting('api_key')
    url_base = '/' + Env.setting('url_base').lstrip('/') if Env.setting('url_base') else ''
    reloader = debug and not options.daemonize

    # Basic config
    app.host = Env.setting('host', default = '0.0.0.0')
    app.port = Env.setting('port', default = 5000)
    app.debug = debug
    app.secret_key = api_key

    # Static path
    web.add_url_rule(url_base + '/static/<path:filename>',
                      endpoint = 'static',
                      view_func = app.send_static_file)

    # Register modules
    app.register_blueprint(web, url_prefix = '%s/' % url_base)
    app.register_blueprint(api, url_prefix = '%s/%s/' % (url_base, api_key))

    # Go go go!
    app.run(use_reloader = reloader)

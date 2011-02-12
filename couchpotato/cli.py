from couchpotato import app
from couchpotato.settings import Settings
from logging import handlers
from optparse import OptionParser
import logging
import os.path
import sys


def cmd_couchpotato(base_path):
    '''Commandline entry point.'''

    # Options
    parser = OptionParser('usage: %prog [options]')
    parser.add_option('-l', '--logdir', dest = 'logdir', default = 'logs', help = 'log DIRECTORY (default ./logs)')
    parser.add_option('-t', '--test', '--debug', action = 'store_true', dest = 'debug', help = 'Debug mode')
    parser.add_option('-q', '--quiet', action = 'store_true', dest = 'quiet', help = "Don't log to console")
    parser.add_option('-d', '--daemon', action = 'store_true', dest = 'daemonize', help = 'Daemonize the app')

    (options, args) = parser.parse_args(sys.argv[1:])


    # Register settings
    settings = Settings(os.path.join(base_path, 'settings.conf'))
    debug = options.debug or settings.get('debug', default = False)


    # Logger
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%H:%M:%S')
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    # To screen
    if debug and not options.quiet:
        hdlr = logging.StreamHandler(sys.stderr)
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)

    # To file
    hdlr2 = handlers.RotatingFileHandler(os.path.join(options.logdir, 'CouchPotato.log'), 'a', 5000000, 4)
    hdlr2.setFormatter(formatter)
    logger.addHandler(hdlr2)


    # Load config
    from couchpotato.settings.loader import SettingsLoader
    sl = SettingsLoader(root = base_path)
    sl.loadConfig('couchpotato', 'core')


    # Create app
    app
    app.host = settings.get('host', default = '0.0.0.0')
    app.port = settings.get('port', default = 5000)
    app.run(debug = debug)

#!/usr/bin/env python
from logging import handlers
from os.path import dirname
import logging
import os
import signal
import subprocess
import sys
import traceback


# Root path
base_path = dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

from couchpotato.core.helpers.variable import getDataDir
data_dir = getDataDir()

# Logging
from couchpotato.core.logger import CPLog
log = CPLog(__name__)

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%H:%M:%S')
hdlr = handlers.RotatingFileHandler(os.path.join(data_dir, 'error.log'), 'a', 500000, 10)
hdlr.setLevel(logging.CRITICAL)
hdlr.setFormatter(formatter)
log.logger.addHandler(hdlr)


class Loader(object):

    do_restart = False

    def __init__(self):

        # Get options via arg
        from couchpotato.runner import getOptions
        self.options = getOptions(base_path, sys.argv[1:])

    def addSignals(self):

        signal.signal(signal.SIGINT, self.onExit)
        signal.signal(signal.SIGTERM, lambda signum, stack_frame: sys.exit(1))

        from couchpotato.core.event import addEvent
        addEvent('app.after_shutdown', self.afterShutdown)

    def afterShutdown(self, restart):
        self.do_restart = restart

    def onExit(self, signal, frame):
        from couchpotato.core.event import fireEvent
        fireEvent('app.crappy_shutdown', single = True)

    def run(self):

        self.addSignals()

        try:
            from couchpotato.runner import runCouchPotato
            runCouchPotato(self.options, base_path, sys.argv[1:])
        except SystemExit as errno:
            if errno is 3:
                raise
        except:
            raise

        if self.do_restart:
            self.restart()

    def restart(self):
        try:
            # remove old pidfile first
            try:
                if self.runAsDaemon():
                    self.daemon.delpid()
            except:
                log.critical(traceback.format_exc())

            args = [sys.executable] + [os.path.join(base_path, __file__)] + sys.argv[1:]
            subprocess.Popen(args)
        except:
            log.critical(traceback.format_exc())

    def daemonize(self):

        if self.runAsDaemon():
            try:
                from daemon import Daemon
                self.daemon = Daemon(self.options.pid_file)
                self.daemon.daemonize()
            except SystemExit:
                raise
            except:
                log.critical(traceback.format_exc())

    def runAsDaemon(self):
        return self.options.daemon and  self.options.pid_file


if __name__ == '__main__':
    try:
        l = Loader()
        l.daemonize()
        l.run()
    except KeyboardInterrupt:
        pass
    except SystemExit:
        raise
    except Exception as (errno, msg):
        if errno != 4:
            log.critical(traceback.format_exc())

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


class Loader(object):

    do_restart = False

    def __init__(self):

        # Get options via arg
        from couchpotato.runner import getOptions
        from couchpotato.core.helpers.variable import getDataDir
        self.options = getOptions(base_path, sys.argv[1:])
        self.data_dir = getDataDir()

        # Logging
        from couchpotato.core.logger import CPLog
        self.log = CPLog(__name__)

        if self.options.daemon:
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%H:%M:%S')
            hdlr = handlers.RotatingFileHandler(os.path.join(self.data_dir, 'logs', 'error.log'), 'a', 500000, 10)
            hdlr.setLevel(logging.CRITICAL)
            hdlr.setFormatter(formatter)
            self.log.logger.addHandler(hdlr)

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
        except (KeyboardInterrupt, SystemExit):
            pass
        except:
            self.log.critical(traceback.format_exc())

        if self.do_restart:
            self.restart()

    def restart(self):
        try:
            # remove old pidfile first
            try:
                if self.runAsDaemon():
                    self.daemon.delpid()
            except:
                self.log.critical(traceback.format_exc())

            args = [sys.executable] + [os.path.join(base_path, __file__)] + sys.argv[1:]
            subprocess.Popen(args)
        except:
            self.log.critical(traceback.format_exc())

    def daemonize(self):

        if self.runAsDaemon():
            try:
                from daemon import Daemon
                self.daemon = Daemon(self.options.pid_file)
                self.daemon.daemonize()
            except SystemExit:
                raise
            except:
                self.log.critical(traceback.format_exc())

    def runAsDaemon(self):
        return self.options.daemon and  self.options.pid_file


if __name__ == '__main__':
    try:
        l = Loader()
        l.daemonize()
        l.run()
    except SystemExit:
        pass
    except:
        l.log.critical(traceback.format_exc())

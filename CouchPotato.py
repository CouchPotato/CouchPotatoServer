#!/usr/bin/env python
from os.path import dirname
import os
import signal
import subprocess
import sys


# Root path
base_path = dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.insert(0, os.path.join(base_path, 'libs'))


class Loader(object):

    do_restart = True

    def __init__(self):

        from couchpotato.core.logger import CPLog
        self.log = CPLog(__name__)

        # Get options via arg
        from couchpotato.runner import getOptions
        from couchpotato.core.helpers.variable import getDataDir
        self.options = getOptions(base_path, sys.argv[1:])
        self.data_dir = getDataDir()

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
        except Exception, e:
            self.log.critical(e)

        if self.do_restart:
            self.restart()

        sys.exit(0)

    def restart(self):
        try:
            args = [sys.executable] + [os.path.join(base_path, __file__)] + sys.argv[1:]
            subprocess.Popen(args)
        except Exception, e:
            self.log.critical(e)
            return 0

    def daemonize(self):

        if self.options.daemon and  self.options.pid_file:
            from daemon import Daemon
            daemon = Daemon(self.options.pid_file)
            daemon.daemonize()


if __name__ == '__main__':
    l = Loader()
    l.daemonize()
    l.run()

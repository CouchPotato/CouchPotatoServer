#!/usr/bin/env python
from os.path import dirname
from signal import signal, SIGTERM
import os
import subprocess
import sys
import time


# Root path
base_path = dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

from couchpotato.core.logger import CPLog
log = CPLog(__name__)

# Get options via arg
from couchpotato.runner import getOptions
from couchpotato.core.helpers.variable import getDataDir
options = getOptions(base_path, sys.argv[1:])
data_dir = getDataDir()

def start():
    try:
        args = [sys.executable] + [os.path.join(base_path, __file__)] + sys.argv[1:]
        new_environ = os.environ.copy()
        new_environ['cp_main'] = 'true'

        if os.name == 'nt':
            for key, value in new_environ.iteritems():
                if isinstance(value, unicode):
                    new_environ[key] = value.encode('iso-8859-1')

        subprocess.call(args, env = new_environ)
        return os.path.isfile(os.path.join(data_dir, 'restart'))
    except KeyboardInterrupt, e:
        pass
    except Exception, e:
        log.critical(e)
        return 0

from couchpotato.runner import runCouchPotato
def main():
    if os.environ.get('cp_main', 'false') == 'true':
        try:
            runCouchPotato(options, base_path, sys.argv[1:])
        except Exception, e:
            log.critical(e)
    else:
        while 1:
            restart = start()
            if not restart:
                break

    from couchpotato.core.event import fireEvent
    fireEvent('app.crappy_shutdown', single = True)
    time.sleep(1)

    sys.exit()

if __name__ == '__main__':

    signal(SIGTERM, lambda signum, stack_frame: sys.exit(1))

    if options.daemon and options.pid_file and not os.environ.get('cp_main'):
        from daemon import Daemon
        daemon = Daemon(options.pid_file)
        daemon.daemonize()

    main()

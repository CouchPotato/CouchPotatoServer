# -*- coding: utf-8 -*-
"""
    livereload.watcher
    ~~~~~~~~~~~~~~~~~~

    A file watch management for LiveReload Server.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import os
import glob
import time


class Watcher(object):
    """A file watcher registery."""
    def __init__(self):
        self._tasks = {}
        self._mtimes = {}

        # filepath that is changed
        self.filepath = None
        self._start = time.time()

    def ignore(self, filename):
        """Ignore a given filename or not."""
        _, ext = os.path.splitext(filename)
        return ext in ['.pyc', '.pyo', '.o', '.swp']

    def watch(self, path, func=None):
        """Add a task to watcher."""
        self._tasks[path] = func

    def start(self, callback):
        """Start the watcher running, calling callback when changes are observed. If this returns False,
        regular polling will be used."""
        return False

    def examine(self):
        """Check if there are changes, if true, run the given task."""
        # clean filepath
        self.filepath = None
        for path in self._tasks:
            if self.is_changed(path):
                func = self._tasks[path]
                # run function
                func and func()
        return self.filepath

    def is_changed(self, path):
        if os.path.isfile(path):
            return self.is_file_changed(path)
        elif os.path.isdir(path):
            return self.is_folder_changed(path)
        return self.is_glob_changed(path)

    def is_file_changed(self, path):
        if not os.path.isfile(path):
            return False

        if self.ignore(path):
            return False

        mtime = os.path.getmtime(path)

        if path not in self._mtimes:
            self._mtimes[path] = mtime
            self.filepath = path
            return mtime > self._start

        if self._mtimes[path] != mtime:
            self._mtimes[path] = mtime
            self.filepath = path
            return True

        self._mtimes[path] = mtime
        return False

    def is_folder_changed(self, path):
        for root, dirs, files in os.walk(path, followlinks=True):
            if '.git' in dirs:
                dirs.remove('.git')
            if '.hg' in dirs:
                dirs.remove('.hg')
            if '.svn' in dirs:
                dirs.remove('.svn')
            if '.cvs' in dirs:
                dirs.remove('.cvs')

            for f in files:
                if self.is_file_changed(os.path.join(root, f)):
                    return True
        return False

    def is_glob_changed(self, path):
        for f in glob.glob(path):
            if self.is_file_changed(f):
                return True
        return False


class INotifyWatcher(Watcher):
    def __init__(self):
        Watcher.__init__(self)

        import pyinotify
        self.wm = pyinotify.WatchManager()
        self.notifier = None
        self.callback = None

    def watch(self, path, func=None):
        import pyinotify
        flag = pyinotify.IN_CREATE | pyinotify.IN_DELETE | pyinotify.IN_MODIFY
        self.wm.add_watch(path, flag, rec=True, do_glob=True, auto_add=True)
        Watcher.watch(self, path, func)

    def inotify_event(self, event):
        self.callback()

    def start(self, callback):
        if not self.notifier:
            self.callback = callback

            import pyinotify
            from tornado import ioloop
            self.notifier = pyinotify.TornadoAsyncNotifier(
                self.wm, ioloop.IOLoop.instance(),
                default_proc_fun=self.inotify_event
            )
            callback()
        return True

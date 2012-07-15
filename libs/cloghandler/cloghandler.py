# Copyright 2008 Lowell Alleman
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may not
#   use this file except in compliance with the License. You may obtain a copy
#   of the License at http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
""" cloghandler.py:  A smart replacement for the standard RotatingFileHandler

ConcurrentRotatingFileHandler:  This class is a log handler which is a drop-in
replacement for the python standard log handler 'RotateFileHandler', the primary
difference being that this handler will continue to write to the same file if
the file cannot be rotated for some reason, whereas the RotatingFileHandler will
strictly adhere to the maximum file size.  Unfortunately, if you are using the
RotatingFileHandler on Windows, you will find that once an attempted rotation
fails, all subsequent log messages are dropped.  The other major advantage of
this module is that multiple processes can safely write to a single log file.

To put it another way:  This module's top priority is preserving your log
records, whereas the standard library attempts to limit disk usage, which can
potentially drop log messages. If you are trying to determine which module to
use, there are number of considerations: What is most important: strict disk
space usage or preservation of log messages? What OSes are you supporting? Can
you afford to have processes blocked by file locks?

Concurrent access is handled by using file locks, which should ensure that log
messages are not dropped or clobbered. This means that a file lock is acquired
and released for every log message that is written to disk. (On Windows, you may
also run into a temporary situation where the log file must be opened and closed
for each log message.) This can have potentially performance implications. In my
testing, performance was more than adequate, but if you need a high-volume or
low-latency solution, I suggest you look elsewhere.

This module currently only support the 'nt' and 'posix' platforms due to the
usage of the portalocker module.  I do not have access to any other platforms
for testing, patches are welcome.

See the README file for an example usage of this module.

"""


__version__ = "$Id: cloghandler.py 6175 2009-11-02 18:40:35Z lowell $"
__author__ = "Lowell Alleman"
__all__ = [
    "ConcurrentRotatingFileHandler",
]


import os
import sys
from random import randint
from logging import Handler
from logging.handlers import BaseRotatingHandler

try:
    import codecs
except ImportError:
    codecs = None



# Question/TODO: Should we have a fallback mode if we can't load portalocker /
# we should still be better off than with the standard RotattingFileHandler
# class, right? We do some rename checking... that should prevent some file
# clobbering that the builtin class allows.

# sibling  module than handles all the ugly platform-specific details of file locking
from portalocker import lock, unlock, LOCK_EX, LOCK_NB, LockException


# A client can set this to true to automatically convert relative paths to
# absolute paths (which will also hide the absolute path warnings)
FORCE_ABSOLUTE_PATH = False


class ConcurrentRotatingFileHandler(BaseRotatingHandler):
    """
    Handler for logging to a set of files, which switches from one file to the
    next when the current file reaches a certain size. Multiple processes can
    write to the log file concurrently, but this may mean that the file will
    exceed the given size.
    """
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0,
                 encoding=None, debug=True, supress_abs_warn=False):
        """
        Open the specified file and use it as the stream for logging.

        By default, the file grows indefinitely. You can specify particular
        values of maxBytes and backupCount to allow the file to rollover at
        a predetermined size.

        Rollover occurs whenever the current log file is nearly maxBytes in
        length. If backupCount is >= 1, the system will successively create
        new files with the same pathname as the base file, but with extensions
        ".1", ".2" etc. appended to it. For example, with a backupCount of 5
        and a base file name of "app.log", you would get "app.log",
        "app.log.1", "app.log.2", ... through to "app.log.5". The file being
        written to is always "app.log" - when it gets filled up, it is closed
        and renamed to "app.log.1", and if files "app.log.1", "app.log.2" etc.
        exist, then they are renamed to "app.log.2", "app.log.3" etc.
        respectively.

        If maxBytes is zero, rollover never occurs.

        On Windows, it is not possible to rename a file that is currently opened
        by another process.  This means that it is not possible to rotate the
        log files if multiple processes is using the same log file.  In this
        case, the current log file will continue to grow until the rotation can
        be completed successfully.  In order for rotation to be possible, all of
        the other processes need to close the file first.  A mechanism, called
        "degraded" mode, has been created for this scenario.  In degraded mode,
        the log file is closed after each log message is written.  So once all
        processes have entered degraded mode, the next rotate log attempt should
        be successful and then normal logging can be resumed.

        This log handler assumes that all concurrent processes logging to a
        single file will are using only this class, and that the exact same
        parameters are provided to each instance of this class.  If, for
        example, two different processes are using this class, but with
        different values for 'maxBytes' or 'backupCount', then odd behavior is
        expected. The same is true if this class is used by one application, but
        the RotatingFileHandler is used by another.

        NOTE:  You should always provide 'filename' as an absolute path, since
        this class will need to re-open the file during rotation. If your
        application call os.chdir() then subsequent log files could be created
        in the wrong directory.
        """
        # The question of absolute paths: I'm not sure what the 'right thing' is
        # to do here. RotatingFileHander simply ignores this possibility. I was
        # going call os.path.abspath(), but that potentially limits uses. For
        # example, on Linux (any posix system?) you can rename a directory of a
        # running app, and the app wouldn't notice as long as it only opens new
        # files using relative paths. But since that's not a "normal" thing to
        # do, and having an app call os.chdir() is a much more likely scenario
        # that should be supported. For the moment, we are just going to warn
        # the user if they provide a relative path and do some other voodoo
        # logic that you'll just have to review for yourself.
        
        # if the given filename contains no path, we make an absolute path
        if not os.path.isabs(filename):
            if FORCE_ABSOLUTE_PATH or \
               not os.path.split(filename)[0]:
                filename = os.path.abspath(filename)
            elif not supress_abs_warn:
                from warnings import warn
                warn("The given 'filename' should be an absolute path.  If your "
                     "application calls os.chdir(), your logs may get messed up. "
                     "Use 'supress_abs_warn=True' to hide this message.")
        try:
            BaseRotatingHandler.__init__(self, filename, mode, encoding)
        except TypeError: # Due to a different logging release without encoding support  (Python 2.4.1 and earlier?)
            BaseRotatingHandler.__init__(self, filename, mode)
            self.encoding = encoding
        
        self._rotateFailed = False
        self.maxBytes = maxBytes
        self.backupCount = backupCount
        # Prevent multiple extensions on the lock file (Only handles the normal "*.log" case.)
        if filename.endswith(".log"):
            lock_file = filename[:-4]
        else:
            lock_file = filename
        self.stream_lock = open(lock_file + ".lock", "w")
        
        # For debug mode, swap out the "_degrade()" method with a more a verbose one.
        if debug:
            self._degrade = self._degrade_debug
    
    def _openFile(self, mode):
        if self.encoding:
            self.stream = codecs.open(self.baseFilename, mode, self.encoding)
        else:
            self.stream = open(self.baseFilename, mode)
    
    def acquire(self):
        """ Acquire thread and file locks. Also re-opening log file when running
        in 'degraded' mode. """
        # handle thread lock
        Handler.acquire(self)
        lock(self.stream_lock, LOCK_EX)
        if self.stream.closed:
            self._openFile(self.mode)
    
    def release(self):
        """ Release file and thread locks. Flush stream and take care of closing
        stream in 'degraded' mode. """
        try:
            self.stream.flush()
            if self._rotateFailed:
                self.stream.close()
        finally:
            try:
                unlock(self.stream_lock)
            finally:
                # release thread lock
                Handler.release(self)
    
    def close(self):
        """
        Closes the stream.
        """
        if not self.stream.closed:
            self.stream.flush()
            self.stream.close()
        Handler.close(self)
    
    def flush(self):
        """ flush():  Do nothing.

        Since a flush is issued in release(), we don't do it here. To do a flush
        here, it would be necessary to re-lock everything, and it is just easier
        and cleaner to do it all in release(), rather than requiring two lock
        ops per handle() call.

        Doing a flush() here would also introduces a window of opportunity for
        another process to write to the log file in between calling
        stream.write() and stream.flush(), which seems like a bad thing. """
        pass
    
    def _degrade(self, degrade, msg, *args):
        """ Set degrade mode or not.  Ignore msg. """
        self._rotateFailed = degrade
        del msg, args   # avoid pychecker warnings
    
    def _degrade_debug(self, degrade, msg, *args):
        """ A more colorful version of _degade(). (This is enabled by passing
        "debug=True" at initialization).
        """
        if degrade:
            if not self._rotateFailed:
                sys.stderr.write("Degrade mode - ENTERING - (pid=%d)  %s\n" %
                                 (os.getpid(), msg % args))
                self._rotateFailed = True
        else:
            if self._rotateFailed:
                sys.stderr.write("Degrade mode - EXITING  - (pid=%d)   %s\n" %
                                 (os.getpid(), msg % args))
                self._rotateFailed = False
    
    def doRollover(self):
        """
        Do a rollover, as described in __init__().
        """
        if self.backupCount <= 0:
            # Don't keep any backups, just overwrite the existing backup file
            # Locking doesn't much matter here; since we are overwriting it anyway
            self.stream.close()
            self._openFile("w")
            return
        self.stream.close()
        try:
            # Attempt to rename logfile to tempname:  There is a slight race-condition here, but it seems unavoidable
            tmpname = None
            while not tmpname or os.path.exists(tmpname):
                tmpname = "%s.rotate.%08d" % (self.baseFilename, randint(0,99999999))
            try:
                # Do a rename test to determine if we can successfully rename the log file
                os.rename(self.baseFilename, tmpname)
            except (IOError, OSError):
                exc_value = sys.exc_info()[1]
                self._degrade(True, "rename failed.  File in use?  "
                              "exception=%s", exc_value)
                return
            
            # Q: Is there some way to protect this code from a KeboardInterupt?
            # This isn't necessarily a data loss issue, but it certainly would
            # break the rotation process during my stress testing.
            
            # There is currently no mechanism in place to handle the situation
            # where one of these log files cannot be renamed. (Example, user
            # opens "logfile.3" in notepad)
            for i in range(self.backupCount - 1, 0, -1):
                sfn = "%s.%d" % (self.baseFilename, i)
                dfn = "%s.%d" % (self.baseFilename, i + 1)
                if os.path.exists(sfn):
                    #print "%s -> %s" % (sfn, dfn)
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.baseFilename + ".1"
            if os.path.exists(dfn):
                os.remove(dfn)
            os.rename(tmpname, dfn)
            #print "%s -> %s" % (self.baseFilename, dfn)
            self._degrade(False, "Rotation completed")
        finally:
            self._openFile(self.mode)
    
    def shouldRollover(self, record):
        """
        Determine if rollover should occur.

        For those that are keeping track. This differs from the standard
        library's RotatingLogHandler class. Because there is no promise to keep
        the file size under maxBytes we ignore the length of the current record.
        """
        del record  # avoid pychecker warnings
        if self._shouldRollover():
            # if some other process already did the rollover we might
            # checked log.1, so we reopen the stream and check again on
            # the right log file
            self.stream.close()
            self._openFile(self.mode)
            return self._shouldRollover()
        return False
    
    def _shouldRollover(self):
        if self.maxBytes > 0:                   # are we rolling over?
            self.stream.seek(0, 2)  #due to non-posix-compliant Windows feature
            if self.stream.tell() >= self.maxBytes:
                return True
            else:
                self._degrade(False, "Rotation done or not needed at this time")
        return False


# Publish this class to the "logging.handlers" module so that it can be use 
# from a logging config file via logging.config.fileConfig().
import logging.handlers
logging.handlers.ConcurrentRotatingFileHandler = ConcurrentRotatingFileHandler

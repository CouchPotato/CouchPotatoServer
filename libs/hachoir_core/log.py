import os, sys, time
import hachoir_core.config as config
from hachoir_core.i18n import _

class Log:
    LOG_INFO   = 0
    LOG_WARN   = 1
    LOG_ERROR  = 2

    level_name = {
        LOG_WARN: "[warn]",
        LOG_ERROR: "[err!]",
        LOG_INFO: "[info]"
    }

    def __init__(self):
        self.__buffer = {}
        self.__file = None
        self.use_print = True
        self.use_buffer = False
        self.on_new_message = None # Prototype: def func(level, prefix, text, context)

    def shutdown(self):
        if self.__file:
            self._writeIntoFile(_("Stop Hachoir"))

    def setFilename(self, filename, append=True):
        """
        Use a file to store all messages. The
        UTF-8 encoding will be used. Write an informative
        message if the file can't be created.

        @param filename: C{L{string}}
        """

        # Look if file already exists or not
        filename = os.path.expanduser(filename)
        filename = os.path.realpath(filename)
        append = os.access(filename, os.F_OK)

        # Create log file (or open it in append mode, if it already exists)
        try:
            import codecs
            if append:
                self.__file = codecs.open(filename, "a", "utf-8")
            else:
                self.__file = codecs.open(filename, "w", "utf-8")
            self._writeIntoFile(_("Starting Hachoir"))
        except IOError, err:
            if err.errno == 2:
                self.__file = None
                self.info(_("[Log] setFilename(%s) fails: no such file") % filename)
            else:
                raise

    def _writeIntoFile(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.__file.write(u"%s - %s\n" % (timestamp, message))
        self.__file.flush()

    def newMessage(self, level, text, ctxt=None):
        """
        Write a new message : append it in the buffer,
        display it to the screen (if needed), and write
        it in the log file (if needed).

        @param level: Message level.
        @type level: C{int}
        @param text: Message content.
        @type text: C{str}
        @param ctxt: The caller instance.
        """

        if level < self.LOG_ERROR and config.quiet or \
           level <= self.LOG_INFO and not config.verbose:
            return
        if config.debug:
            from hachoir_core.error import getBacktrace
            backtrace = getBacktrace(None)
            if backtrace:
                text += "\n\n" + backtrace

        _text = text
        if hasattr(ctxt, "_logger"):
            _ctxt = ctxt._logger()
            if _ctxt is not None:
                text = "[%s] %s" % (_ctxt, text)

        # Add message to log buffer
        if self.use_buffer:
            if not self.__buffer.has_key(level):
                self.__buffer[level] = [text]
            else:
                self.__buffer[level].append(text)

        # Add prefix
        prefix = self.level_name.get(level, "[info]")

        # Display on stdout (if used)
        if self.use_print:
            sys.stdout.flush()
            sys.stderr.write("%s %s\n" % (prefix, text))
            sys.stderr.flush()

        # Write into outfile (if used)
        if self.__file:
            self._writeIntoFile("%s %s" % (prefix, text))

        # Use callback (if used)
        if self.on_new_message:
            self.on_new_message (level, prefix, _text, ctxt)

    def info(self, text):
        """
        New informative message.
        @type text: C{str}
        """
        self.newMessage(Log.LOG_INFO, text)

    def warning(self, text):
        """
        New warning message.
        @type text: C{str}
        """
        self.newMessage(Log.LOG_WARN, text)

    def error(self, text):
        """
        New error message.
        @type text: C{str}
        """
        self.newMessage(Log.LOG_ERROR, text)

log = Log()

class Logger(object):
    def _logger(self):
        return "<%s>" % self.__class__.__name__
    def info(self, text):
        log.newMessage(Log.LOG_INFO, text, self)
    def warning(self, text):
        log.newMessage(Log.LOG_WARN, text, self)
    def error(self, text):
        log.newMessage(Log.LOG_ERROR, text, self)

"""
Functions to display an error (error, warning or information) message.
"""

from hachoir_core.log import log
from hachoir_core.tools import makePrintable
import sys, traceback

def getBacktrace(empty="Empty backtrace."):
    """
    Try to get backtrace as string.
    Returns "Error while trying to get backtrace" on failure.
    """
    try:
        info = sys.exc_info()
        trace = traceback.format_exception(*info)
        sys.exc_clear()
        if trace[0] != "None\n":
            return "".join(trace)
    except:
        # No i18n here (imagine if i18n function calls error...)
        return "Error while trying to get backtrace"
    return empty

class HachoirError(Exception):
    """
    Parent of all errors in Hachoir library
    """
    def __init__(self, message):
        message_bytes = makePrintable(message, "ASCII")
        Exception.__init__(self, message_bytes)
        self.text = message

    def __unicode__(self):
        return self.text

# Error classes which may be raised by Hachoir core
# FIXME: Add EnvironmentError (IOError or OSError) and AssertionError?
# FIXME: Remove ArithmeticError and RuntimeError?
HACHOIR_ERRORS = (HachoirError, LookupError, NameError, AttributeError,
    TypeError, ValueError, ArithmeticError, RuntimeError)

info    = log.info
warning = log.warning
error   = log.error

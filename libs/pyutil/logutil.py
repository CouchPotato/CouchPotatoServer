# Copyright (c) 2005-2010 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

# This little file makes it so that we can use "log.msg()" and the contents
# get logged to the Twisted logger if present, else to the Python Standard
# Library logger.

import warnings
warnings.warn("deprecated", DeprecationWarning)
try:
    from twisted.python import log
    log # http://divmod.org/trac/ticket/1499
except ImportError:
    import logging
    class MinimalLogger:
        def msg(self, m):
            logging.log(0, m)
    log = MinimalLogger()


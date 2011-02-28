"""
_logging module (imdb package).

This module provides the logging facilities used by the imdb package.

Copyright 2009-2010 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import logging

LEVELS = {'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARNING,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL}


imdbpyLogger = logging.getLogger('imdbpy')
imdbpyStreamHandler = logging.StreamHandler()
imdbpyFormatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s]' \
                                    ' %(pathname)s:%(lineno)d: %(message)s')
imdbpyStreamHandler.setFormatter(imdbpyFormatter)
imdbpyLogger.addHandler(imdbpyStreamHandler)

def setLevel(level):
    """Set logging level for the main logger."""
    level = level.lower().strip()
    imdbpyLogger.setLevel(LEVELS.get(level, logging.NOTSET))
    imdbpyLogger.log(imdbpyLogger.level, 'set logging threshold to "%s"',
                    logging.getLevelName(imdbpyLogger.level))


#imdbpyLogger.setLevel(logging.DEBUG)


# It can be an idea to have a single function to log and warn:
#import warnings
#def log_and_warn(msg, args=None, logger=None, level=None):
#    """Log the message and issue a warning."""
#    if logger is None:
#        logger = imdbpyLogger
#    if level is None:
#        level = logging.WARNING
#    if args is None:
#        args = ()
#    #warnings.warn(msg % args, stacklevel=0)
#    logger.log(level, msg % args)


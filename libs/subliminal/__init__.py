# -*- coding: utf-8 -*-
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
from .api import list_subtitles, download_subtitles
from .async import Pool
from .core import (SERVICES, LANGUAGE_INDEX, SERVICE_INDEX, SERVICE_CONFIDENCE,
    MATCHING_CONFIDENCE)
from .infos import __version__
import logging
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass


__all__ = ['SERVICES', 'LANGUAGE_INDEX', 'SERVICE_INDEX', 'SERVICE_CONFIDENCE',
           'MATCHING_CONFIDENCE', 'list_subtitles', 'download_subtitles', 'Pool']
logging.getLogger(__name__).addHandler(NullHandler())

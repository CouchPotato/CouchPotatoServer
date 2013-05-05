#!/usr/bin/env python
"""Python codec for CSS."""
__docformat__ = 'restructuredtext'
__author__ = 'Walter Doerwald'
__version__ = '$Id: util.py 1114 2008-03-05 13:22:59Z cthedot $'

import sys

if sys.version_info < (3,):
    from _codec2 import *
    # for tests
    from _codec2 import _fixencoding
else:
    from _codec3 import *
    # for tests
    from _codec3 import _fixencoding

# -*- coding: utf-8 -*-
"""
    sleekxmpp.util
    ~~~~~~~~~~~~~~

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2012 Nathanael C. Fritz, Lance J.T. Stout
    :license: MIT, see LICENSE for more details
"""


from sleekxmpp.util.misc_ops import bytes, unicode, hashes, hash, \
                                    num_to_bytes, bytes_to_num, quote, XOR


# =====================================================================
# Standardize import of Queue class:

import sys
if 'gevent' in sys.modules:
    import gevent.queue as queue
    Queue = queue.JoinableQueue
else:
    try:
        import queue
    except ImportError:
        import Queue as queue
    Queue = queue.Queue

QueueEmpty = queue.Empty

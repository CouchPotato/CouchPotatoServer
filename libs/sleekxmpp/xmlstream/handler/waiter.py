# -*- coding: utf-8 -*-
"""
    sleekxmpp.xmlstream.handler.waiter
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2011 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""

import logging

from sleekxmpp.util import Queue, QueueEmpty
from sleekxmpp.xmlstream.handler.base import BaseHandler


log = logging.getLogger(__name__)


class Waiter(BaseHandler):

    """
    The Waiter handler allows an event handler to block until a
    particular stanza has been received. The handler will either be
    given the matched stanza, or ``False`` if the waiter has timed out.

    :param string name: The name of the handler.
    :param matcher: A :class:`~sleekxmpp.xmlstream.matcher.base.MatcherBase`
                    derived object for matching stanza objects.
    :param stream: The :class:`~sleekxmpp.xmlstream.xmlstream.XMLStream`
                   instance this handler should monitor.
    """

    def __init__(self, name, matcher, stream=None):
        BaseHandler.__init__(self, name, matcher, stream=stream)
        self._payload = Queue()

    def prerun(self, payload):
        """Store the matched stanza when received during processing.

        :param payload: The matched
            :class:`~sleekxmpp.xmlstream.stanzabase.ElementBase` object.
        """
        self._payload.put(payload)

    def run(self, payload):
        """Do not process this handler during the main event loop."""
        pass

    def wait(self, timeout=None):
        """Block an event handler while waiting for a stanza to arrive.

        Be aware that this will impact performance if called from a
        non-threaded event handler.

        Will return either the received stanza, or ``False`` if the
        waiter timed out.

        :param int timeout: The number of seconds to wait for the stanza
            to arrive. Defaults to the the stream's
            :class:`~sleekxmpp.xmlstream.xmlstream.XMLStream.response_timeout`
            value.
        """
        if timeout is None:
            timeout = self.stream().response_timeout

        elapsed_time = 0
        stanza = False
        while elapsed_time < timeout and not self.stream().stop.is_set():
            try:
                stanza = self._payload.get(True, 1)
                break
            except QueueEmpty:
                elapsed_time += 1
                if elapsed_time >= timeout:
                    log.warning("Timed out waiting for %s", self.name)
        self.stream().remove_handler(self.name)
        return stanza

    def check_delete(self):
        """Always remove waiters after use."""
        return True

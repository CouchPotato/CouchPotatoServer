"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream.handler import Waiter


class XMLWaiter(Waiter):

    """
    The XMLWaiter class is identical to the normal Waiter class
    except that it returns the XML contents of the stanza instead
    of the full stanza object itself.

    Methods:
        prerun -- Overrides Waiter.prerun
    """

    def prerun(self, payload):
        """
        Store the XML contents of the stanza to return to the
        waiting event handler.

        Overrides Waiter.prerun

        Arguments:
            payload -- The matched stanza object.
        """
        Waiter.prerun(self, payload.xml)

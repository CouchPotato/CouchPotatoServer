"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream.handler import Callback


class XMLCallback(Callback):

    """
    The XMLCallback class is identical to the normal Callback class,
    except that XML contents of matched stanzas will be processed instead
    of the stanza objects themselves.

    Methods:
        run -- Overrides Callback.run
    """

    def run(self, payload, instream=False):
        """
        Execute the callback function with the matched stanza's
        XML contents, instead of the stanza itself.

        Overrides BaseHandler.run

        Arguments:
            payload  -- The matched stanza object.
            instream -- Force the handler to execute during
                        stream processing. Used only by prerun.
                        Defaults to False.
        """
        Callback.run(self, payload.xml, instream)

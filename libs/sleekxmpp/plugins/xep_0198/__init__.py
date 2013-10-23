"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0198.stanza import Enable, Enabled
from sleekxmpp.plugins.xep_0198.stanza import Resume, Resumed
from sleekxmpp.plugins.xep_0198.stanza import Failed
from sleekxmpp.plugins.xep_0198.stanza import StreamManagement
from sleekxmpp.plugins.xep_0198.stanza import Ack, RequestAck

from sleekxmpp.plugins.xep_0198.stream_management import XEP_0198


register_plugin(XEP_0198)

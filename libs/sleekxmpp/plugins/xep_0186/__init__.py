"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0186 import stanza
from sleekxmpp.plugins.xep_0186.stanza import Invisible, Visible
from sleekxmpp.plugins.xep_0186.invisible_command import XEP_0186


register_plugin(XEP_0186)

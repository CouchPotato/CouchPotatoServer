"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp.plugins import BasePlugin
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins.xep_0221 import stanza, Media, URI
from sleekxmpp.plugins.xep_0004 import FormField


log = logging.getLogger(__name__)


class XEP_0221(BasePlugin):

    name = 'xep_0221'
    description = 'XEP-0221: Data Forms Media Element'
    dependencies = set(['xep_0004'])

    def plugin_init(self):
        register_stanza_plugin(FormField, Media)

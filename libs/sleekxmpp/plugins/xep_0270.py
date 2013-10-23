"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins import BasePlugin, register_plugin


class XEP_0270(BasePlugin):

    name = 'xep_0270'
    description = 'XEP-0270: XMPP Compliance Suites 2010'
    dependencies = set(['xep_0030', 'xep_0115', 'xep_0054',
                        'xep_0163', 'xep_0045', 'xep_0085'])


register_plugin(XEP_0270)

"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins import BasePlugin, register_plugin


class XEP_0302(BasePlugin):

    name = 'xep_0302'
    description = 'XEP-0302: XMPP Compliance Suites 2012'
    dependencies = set(['xep_0030', 'xep_0115', 'xep_0054',
                        'xep_0163', 'xep_0045', 'xep_0085',
                        'xep_0184', 'xep_0198'])


register_plugin(XEP_0302)

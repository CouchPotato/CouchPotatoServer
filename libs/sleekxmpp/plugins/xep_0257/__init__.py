"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.xep_0257 import stanza
from sleekxmpp.plugins.xep_0257.stanza import Certs, AppendCert
from sleekxmpp.plugins.xep_0257.stanza import DisableCert, RevokeCert
from sleekxmpp.plugins.xep_0257.client_cert_management import XEP_0257


register_plugin(XEP_0257)

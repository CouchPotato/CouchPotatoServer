"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp import Iq
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins.xep_0257 import stanza, Certs
from sleekxmpp.plugins.xep_0257 import AppendCert, DisableCert, RevokeCert


log = logging.getLogger(__name__)


class XEP_0257(BasePlugin):

    name = 'xep_0257'
    description = 'XEP-0258: Client Certificate Management for SASL EXTERNAL'
    dependencies = set(['xep_0030'])
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Iq, Certs)
        register_stanza_plugin(Iq, AppendCert)
        register_stanza_plugin(Iq, DisableCert)
        register_stanza_plugin(Iq, RevokeCert)

    def get_certs(self, ifrom=None, block=True, timeout=None, callback=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'get'
        iq['from'] = ifrom
        iq.enable('sasl_certs')
        return iq.send(block=block, timeout=timeout, callback=callback)

    def add_cert(self, name, cert, allow_management=True, ifrom=None,
                       block=True, timeout=None, callback=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom
        iq['sasl_cert_append']['name'] = name
        iq['sasl_cert_append']['x509cert'] = cert
        iq['sasl_cert_append']['cert_management'] = allow_management
        return iq.send(block=block, timeout=timeout, callback=callback)

    def disable_cert(self, name, ifrom=None, block=True,
                           timeout=None, callback=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom
        iq['sasl_cert_disable']['name'] = name
        return iq.send(block=block, timeout=timeout, callback=callback)

    def revoke_cert(self, name, ifrom=None, block=True,
                           timeout=None, callback=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom
        iq['sasl_cert_revoke']['name'] = name
        return iq.send(block=block, timeout=timeout, callback=callback)

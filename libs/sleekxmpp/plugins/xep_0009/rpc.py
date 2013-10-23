"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Dann Martens (TOMOTON).
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp import Iq
from sleekxmpp.xmlstream import ET, register_stanza_plugin
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import MatchXPath
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.plugins.xep_0009 import stanza
from sleekxmpp.plugins.xep_0009.stanza.RPC import RPCQuery, MethodCall, MethodResponse


log = logging.getLogger(__name__)


class XEP_0009(BasePlugin):

    name = 'xep_0009'
    description = 'XEP-0009: Jabber-RPC'
    dependencies = set(['xep_0030'])
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Iq, RPCQuery)
        register_stanza_plugin(RPCQuery, MethodCall)
        register_stanza_plugin(RPCQuery, MethodResponse)

        self.xmpp.registerHandler(
            Callback('RPC Call', MatchXPath('{%s}iq/{%s}query/{%s}methodCall' % (self.xmpp.default_ns, RPCQuery.namespace, RPCQuery.namespace)),
            self._handle_method_call)
        )
        self.xmpp.registerHandler(
            Callback('RPC Call', MatchXPath('{%s}iq/{%s}query/{%s}methodResponse' % (self.xmpp.default_ns, RPCQuery.namespace, RPCQuery.namespace)),
            self._handle_method_response)
        )
        self.xmpp.registerHandler(
            Callback('RPC Call', MatchXPath('{%s}iq/{%s}error' % (self.xmpp.default_ns, self.xmpp.default_ns)),
            self._handle_error)
        )
        self.xmpp.add_event_handler('jabber_rpc_method_call', self._on_jabber_rpc_method_call)
        self.xmpp.add_event_handler('jabber_rpc_method_response', self._on_jabber_rpc_method_response)
        self.xmpp.add_event_handler('jabber_rpc_method_fault', self._on_jabber_rpc_method_fault)
        self.xmpp.add_event_handler('jabber_rpc_error', self._on_jabber_rpc_error)
        self.xmpp.add_event_handler('error', self._handle_error)
        #self.activeCalls = []

        self.xmpp['xep_0030'].add_feature('jabber:iq:rpc')
        self.xmpp['xep_0030'].add_identity('automation','rpc')

    def make_iq_method_call(self, pto, pmethod, params):
        iq = self.xmpp.makeIqSet()
        iq.attrib['to'] = pto
        iq.attrib['from'] = self.xmpp.boundjid.full
        iq.enable('rpc_query')
        iq['rpc_query']['method_call']['method_name'] = pmethod
        iq['rpc_query']['method_call']['params'] = params
        return iq;

    def make_iq_method_response(self, pid, pto, params):
        iq = self.xmpp.makeIqResult(pid)
        iq.attrib['to'] = pto
        iq.attrib['from'] = self.xmpp.boundjid.full
        iq.enable('rpc_query')
        iq['rpc_query']['method_response']['params'] = params
        return iq

    def make_iq_method_response_fault(self, pid, pto, params):
        iq = self.xmpp.makeIqResult(pid)
        iq.attrib['to'] = pto
        iq.attrib['from'] = self.xmpp.boundjid.full
        iq.enable('rpc_query')
        iq['rpc_query']['method_response']['params'] = None
        iq['rpc_query']['method_response']['fault'] = params
        return iq

#    def make_iq_method_error(self, pto, pid, pmethod, params, code, type, condition):
#        iq = self.xmpp.makeIqError(pid)
#        iq.attrib['to'] = pto
#        iq.attrib['from'] = self.xmpp.boundjid.full
#        iq['error']['code'] = code
#        iq['error']['type'] = type
#        iq['error']['condition'] = condition
#        iq['rpc_query']['method_call']['method_name'] = pmethod
#        iq['rpc_query']['method_call']['params'] = params
#        return iq

    def _item_not_found(self, iq):
        payload = iq.get_payload()
        iq.reply().error().set_payload(payload);
        iq['error']['code'] = '404'
        iq['error']['type'] = 'cancel'
        iq['error']['condition'] = 'item-not-found'
        return iq

    def _undefined_condition(self, iq):
        payload = iq.get_payload()
        iq.reply().error().set_payload(payload)
        iq['error']['code'] = '500'
        iq['error']['type'] = 'cancel'
        iq['error']['condition'] = 'undefined-condition'
        return iq

    def _forbidden(self, iq):
        payload = iq.get_payload()
        iq.reply().error().set_payload(payload)
        iq['error']['code'] = '403'
        iq['error']['type'] = 'auth'
        iq['error']['condition'] = 'forbidden'
        return iq

    def _recipient_unvailable(self, iq):
        payload = iq.get_payload()
        iq.reply().error().set_payload(payload)
        iq['error']['code'] = '404'
        iq['error']['type'] = 'wait'
        iq['error']['condition'] = 'recipient-unavailable'
        return iq

    def _handle_method_call(self, iq):
        type = iq['type']
        if type == 'set':
            log.debug("Incoming Jabber-RPC call from %s", iq['from'])
            self.xmpp.event('jabber_rpc_method_call', iq)
        else:
            if type == 'error' and ['rpc_query'] is None:
                self.handle_error(iq)
            else:
                log.debug("Incoming Jabber-RPC error from %s", iq['from'])
                self.xmpp.event('jabber_rpc_error', iq)

    def _handle_method_response(self, iq):
        if iq['rpc_query']['method_response']['fault'] is not None:
            log.debug("Incoming Jabber-RPC fault from %s", iq['from'])
            #self._on_jabber_rpc_method_fault(iq)
            self.xmpp.event('jabber_rpc_method_fault', iq)
        else:
            log.debug("Incoming Jabber-RPC response from %s", iq['from'])
            self.xmpp.event('jabber_rpc_method_response', iq)

    def _handle_error(self, iq):
        print("['XEP-0009']._handle_error -> ERROR! Iq is '%s'" % iq)
        print("#######################")
        print("### NOT IMPLEMENTED ###")
        print("#######################")

    def _on_jabber_rpc_method_call(self, iq, forwarded=False):
        """
        A default handler for Jabber-RPC method call. If another
        handler is registered, this one will defer and not run.

        If this handler is called by your own custom handler with
        forwarded set to True, then it will run as normal.
        """
        if not forwarded and self.xmpp.event_handled('jabber_rpc_method_call') > 1:
            return
        # Reply with error by default
        error = self.client.plugin['xep_0009']._item_not_found(iq)
        error.send()

    def _on_jabber_rpc_method_response(self, iq, forwarded=False):
        """
        A default handler for Jabber-RPC method response. If another
        handler is registered, this one will defer and not run.

        If this handler is called by your own custom handler with
        forwarded set to True, then it will run as normal.
        """
        if not forwarded and self.xmpp.event_handled('jabber_rpc_method_response') > 1:
            return
        error = self.client.plugin['xep_0009']._recpient_unavailable(iq)
        error.send()

    def _on_jabber_rpc_method_fault(self, iq, forwarded=False):
        """
        A default handler for Jabber-RPC fault response. If another
        handler is registered, this one will defer and not run.

        If this handler is called by your own custom handler with
        forwarded set to True, then it will run as normal.
        """
        if not forwarded and self.xmpp.event_handled('jabber_rpc_method_fault') > 1:
            return
        error = self.client.plugin['xep_0009']._recpient_unavailable(iq)
        error.send()

    def _on_jabber_rpc_error(self, iq, forwarded=False):
        """
        A default handler for Jabber-RPC error response. If another
        handler is registered, this one will defer and not run.

        If this handler is called by your own custom handler with
        forwarded set to True, then it will run as normal.
        """
        if not forwarded and self.xmpp.event_handled('jabber_rpc_error') > 1:
            return
        error = self.client.plugin['xep_0009']._recpient_unavailable(iq, iq.get_payload())
        error.send()

    def _send_fault(self, iq, fault_xml): #
        fault = self.make_iq_method_response_fault(iq['id'], iq['from'], fault_xml)
        fault.send()

    def _send_error(self, iq):
        print("['XEP-0009']._send_error -> ERROR! Iq is '%s'" % iq)
        print("#######################")
        print("### NOT IMPLEMENTED ###")
        print("#######################")

    def _extract_method(self, stanza):
        xml = ET.fromstring("%s" % stanza)
        return xml.find("./methodCall/methodName").text

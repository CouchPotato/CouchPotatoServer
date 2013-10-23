"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Dann Martens (TOMOTON).
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream.stanzabase import ElementBase
from xml.etree import cElementTree as ET


class RPCQuery(ElementBase):
    name = 'query'
    namespace = 'jabber:iq:rpc'
    plugin_attrib = 'rpc_query'
    interfaces = set(())
    subinterfaces = set(())
    plugin_attrib_map = {}
    plugin_tag_map = {}


class MethodCall(ElementBase):
    name = 'methodCall'
    namespace = 'jabber:iq:rpc'
    plugin_attrib = 'method_call'
    interfaces = set(('method_name', 'params'))
    subinterfaces = set(())
    plugin_attrib_map = {}
    plugin_tag_map = {}

    def get_method_name(self):
        return self._get_sub_text('methodName')

    def set_method_name(self, value):
        return self._set_sub_text('methodName', value)

    def get_params(self):
        return self.xml.find('{%s}params' % self.namespace)

    def set_params(self, params):
        self.append(params)


class MethodResponse(ElementBase):
    name = 'methodResponse'
    namespace = 'jabber:iq:rpc'
    plugin_attrib = 'method_response'
    interfaces = set(('params', 'fault'))
    subinterfaces = set(())
    plugin_attrib_map = {}
    plugin_tag_map = {}

    def get_params(self):
        return self.xml.find('{%s}params' % self.namespace)

    def set_params(self, params):
        self.append(params)

    def get_fault(self):
        return self.xml.find('{%s}fault' % self.namespace)

    def set_fault(self, fault):
        self.append(fault)

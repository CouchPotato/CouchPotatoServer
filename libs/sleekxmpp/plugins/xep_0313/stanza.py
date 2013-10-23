"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permissio
"""

import datetime as dt

from sleekxmpp.jid import JID
from sleekxmpp.xmlstream import ElementBase, ET
from sleekxmpp.plugins import xep_0082


class MAM(ElementBase):
    name = 'query'
    namespace = 'urn:xmpp:mam:tmp'
    plugin_attrib = 'mam'
    interfaces = set(['queryid', 'start', 'end', 'with', 'results'])
    sub_interfaces = set(['start', 'end', 'with'])

    def setup(self, xml=None):
        ElementBase.setup(self, xml)
        self._results = []

    def get_start(self):
        timestamp = self._get_attr('start')
        return xep_0082.parse(timestamp)

    def set_start(self, value):
        if isinstance(value, dt.datetime):
            value = xep_0082.format_datetime(value)
        self._set_attr('start', value)

    def get_end(self):
        timestamp = self._get_sub_text('end')
        return xep_0082.parse(timestamp)

    def set_end(self, value):
        if isinstance(value, dt.datetime):
            value = xep_0082.format_datetime(value)
        self._set_sub_text('end', value)

    def get_with(self):
        return JID(self._get_sub_text('with'))

    def set_with(self, value):
        self._set_sub_text('with', str(value))

    # The results interface is meant only as an easy
    # way to access the set of collected message responses
    # from the query.

    def get_results(self):
        return self._results

    def set_results(self, values):
        self._results = values

    def del_results(self):
        self._results = []


class Preferences(ElementBase):
    name = 'prefs'
    namespace = 'urn:xmpp:mam:tmp'
    plugin_attrib = 'mam_prefs'
    interfaces = set(['default', 'always', 'never'])
    sub_interfaces = set(['always', 'never'])

    def get_always(self):
        results = set()

        jids = self.xml.findall('{%s}always/{%s}jid' % (
            self.namespace, self.namespace))

        for jid in jids:
            results.add(JID(jid.text))

        return results

    def set_always(self, value):
        self._set_sub_text('always', '', keep=True)
        always = self.xml.find('{%s}always' % self.namespace)
        always.clear()

        if not isinstance(value, (list, set)):
            value = [value]

        for jid in value:
            jid_xml = ET.Element('{%s}jid' % self.namespace)
            jid_xml.text = str(jid)
            always.append(jid_xml)

    def get_never(self):
        results = set()

        jids = self.xml.findall('{%s}never/{%s}jid' % (
            self.namespace, self.namespace))

        for jid in jids:
            results.add(JID(jid.text))

        return results

    def set_never(self, value):
        self._set_sub_text('never', '', keep=True)
        never = self.xml.find('{%s}never' % self.namespace)
        never.clear()

        if not isinstance(value, (list, set)):
            value = [value]

        for jid in value:
            jid_xml = ET.Element('{%s}jid' % self.namespace)
            jid_xml.text = str(jid)
            never.append(jid_xml)


class Result(ElementBase):
    name = 'result'
    namespace = 'urn:xmpp:mam:tmp'
    plugin_attrib = 'mam_result'
    interfaces = set(['forwarded', 'queryid', 'id'])

    def get_forwarded(self):
        return self.parent()['forwarded']

    def del_forwarded(self):
        del self.parent()['forwarded']

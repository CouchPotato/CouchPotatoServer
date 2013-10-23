"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import unittest
from xml.parsers.expat import ExpatError

import sleekxmpp
from sleekxmpp import ClientXMPP, ComponentXMPP
from sleekxmpp.util import Queue
from sleekxmpp.stanza import Message, Iq, Presence
from sleekxmpp.test import TestSocket, TestLiveSocket
from sleekxmpp.exceptions import XMPPError, IqTimeout, IqError
from sleekxmpp.xmlstream import ET, register_stanza_plugin
from sleekxmpp.xmlstream import ElementBase, StanzaBase
from sleekxmpp.xmlstream.tostring import tostring
from sleekxmpp.xmlstream.matcher import StanzaPath, MatcherId
from sleekxmpp.xmlstream.matcher import MatchXMLMask, MatchXPath


class SleekTest(unittest.TestCase):

    """
    A SleekXMPP specific TestCase class that provides
    methods for comparing message, iq, and presence stanzas.

    Methods:
        Message              -- Create a Message stanza object.
        Iq                   -- Create an Iq stanza object.
        Presence             -- Create a Presence stanza object.
        check_jid            -- Check a JID and its component parts.
        check                -- Compare a stanza against an XML string.
        stream_start         -- Initialize a dummy XMPP client.
        stream_close         -- Disconnect the XMPP client.
        make_header          -- Create a stream header.
        send_header          -- Check that the given header has been sent.
        send_feature         -- Send a raw XML element.
        send                 -- Check that the XMPP client sent the given
                                generic stanza.
        recv                 -- Queue data for XMPP client to receive, or
                                verify the data that was received from a
                                live connection.
        recv_header          -- Check that a given stream header
                                was received.
        recv_feature         -- Check that a given, raw XML element
                                was recveived.
        fix_namespaces       -- Add top-level namespace to an XML object.
        compare              -- Compare XML objects against each other.
    """

    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.xmpp = None

    def parse_xml(self, xml_string):
        try:
            xml = ET.fromstring(xml_string)
            return xml
        except (SyntaxError, ExpatError) as e:
            msg = e.msg if hasattr(e, 'msg') else e.message
            if 'unbound' in msg:
                known_prefixes = {
                        'stream': 'http://etherx.jabber.org/streams'}

                prefix = xml_string.split('<')[1].split(':')[0]
                if prefix in known_prefixes:
                    xml_string = '<fixns xmlns:%s="%s">%s</fixns>' % (
                            prefix,
                            known_prefixes[prefix],
                            xml_string)
                xml = self.parse_xml(xml_string)
                xml = list(xml)[0]
                return xml
            else:
                self.fail("XML data was mal-formed:\n%s" % xml_string)

    # ------------------------------------------------------------------
    # Shortcut methods for creating stanza objects

    def Message(self, *args, **kwargs):
        """
        Create a Message stanza.

        Uses same arguments as StanzaBase.__init__

        Arguments:
            xml -- An XML object to use for the Message's values.
        """
        return Message(self.xmpp, *args, **kwargs)

    def Iq(self, *args, **kwargs):
        """
        Create an Iq stanza.

        Uses same arguments as StanzaBase.__init__

        Arguments:
            xml -- An XML object to use for the Iq's values.
        """
        return Iq(self.xmpp, *args, **kwargs)

    def Presence(self, *args, **kwargs):
        """
        Create a Presence stanza.

        Uses same arguments as StanzaBase.__init__

        Arguments:
            xml -- An XML object to use for the Iq's values.
        """
        return Presence(self.xmpp, *args, **kwargs)

    def check_jid(self, jid, user=None, domain=None, resource=None,
                  bare=None, full=None, string=None):
        """
        Verify the components of a JID.

        Arguments:
            jid      -- The JID object to test.
            user     -- Optional. The user name portion of the JID.
            domain   -- Optional. The domain name portion of the JID.
            resource -- Optional. The resource portion of the JID.
            bare     -- Optional. The bare JID.
            full     -- Optional. The full JID.
            string   -- Optional. The string version of the JID.
        """
        if user is not None:
            self.assertEqual(jid.user, user,
                    "User does not match: %s" % jid.user)
        if domain is not None:
            self.assertEqual(jid.domain, domain,
                    "Domain does not match: %s" % jid.domain)
        if resource is not None:
            self.assertEqual(jid.resource, resource,
                    "Resource does not match: %s" % jid.resource)
        if bare is not None:
            self.assertEqual(jid.bare, bare,
                    "Bare JID does not match: %s" % jid.bare)
        if full is not None:
            self.assertEqual(jid.full, full,
                    "Full JID does not match: %s" % jid.full)
        if string is not None:
            self.assertEqual(str(jid), string,
                    "String does not match: %s" % str(jid))

    def check_roster(self, owner, jid, name=None, subscription=None,
                     afrom=None, ato=None, pending_out=None, pending_in=None,
                     groups=None):
        roster = self.xmpp.roster[owner][jid]
        if name is not None:
            self.assertEqual(roster['name'], name,
                    "Incorrect name value: %s" % roster['name'])
        if subscription is not None:
            self.assertEqual(roster['subscription'], subscription,
                    "Incorrect subscription: %s" % roster['subscription'])
        if afrom is not None:
            self.assertEqual(roster['from'], afrom,
                    "Incorrect from state: %s" % roster['from'])
        if ato is not None:
            self.assertEqual(roster['to'], ato,
                    "Incorrect to state: %s" % roster['to'])
        if pending_out is not None:
            self.assertEqual(roster['pending_out'], pending_out,
                    "Incorrect pending_out state: %s" % roster['pending_out'])
        if pending_in is not None:
            self.assertEqual(roster['pending_in'], pending_out,
                    "Incorrect pending_in state: %s" % roster['pending_in'])
        if groups is not None:
            self.assertEqual(roster['groups'], groups,
                    "Incorrect groups: %s" % roster['groups'])

    # ------------------------------------------------------------------
    # Methods for comparing stanza objects to XML strings

    def check(self, stanza, criteria, method='exact',
              defaults=None, use_values=True):
        """
        Create and compare several stanza objects to a correct XML string.

        If use_values is False, tests using stanza.values will not be used.

        Some stanzas provide default values for some interfaces, but
        these defaults can be problematic for testing since they can easily
        be forgotten when supplying the XML string. A list of interfaces that
        use defaults may be provided and the generated stanzas will use the
        default values for those interfaces if needed.

        However, correcting the supplied XML is not possible for interfaces
        that add or remove XML elements. Only interfaces that map to XML
        attributes may be set using the defaults parameter. The supplied XML
        must take into account any extra elements that are included by default.

        Arguments:
            stanza       -- The stanza object to test.
            criteria     -- An expression the stanza must match against.
            method       -- The type of matching to use; one of:
                            'exact', 'mask', 'id', 'xpath', and 'stanzapath'.
                            Defaults to the value of self.match_method.
            defaults     -- A list of stanza interfaces that have default
                            values. These interfaces will be set to their
                            defaults for the given and generated stanzas to
                            prevent unexpected test failures.
            use_values   -- Indicates if testing using stanza.values should
                            be used. Defaults to True.
        """
        if method is None and hasattr(self, 'match_method'):
            method = getattr(self, 'match_method')

        if method != 'exact':
            matchers = {'stanzapath': StanzaPath,
                        'xpath': MatchXPath,
                        'mask': MatchXMLMask,
                        'id': MatcherId}
            Matcher = matchers.get(method, None)
            if Matcher is None:
                raise ValueError("Unknown matching method.")
            test = Matcher(criteria)
            self.failUnless(test.match(stanza),
                    "Stanza did not match using %s method:\n" % method + \
                    "Criteria:\n%s\n" % str(criteria) + \
                    "Stanza:\n%s" % str(stanza))
        else:
            stanza_class = stanza.__class__
            if not isinstance(criteria, ElementBase):
                xml = self.parse_xml(criteria)
            else:
                xml = criteria.xml

            # Ensure that top level namespaces are used, even if they
            # were not provided.
            self.fix_namespaces(stanza.xml, 'jabber:client')
            self.fix_namespaces(xml, 'jabber:client')

            stanza2 = stanza_class(xml=xml)

            if use_values:
                # Using stanza.values will add XML for any interface that
                # has a default value. We need to set those defaults on
                # the existing stanzas and XML so that they will compare
                # correctly.
                default_stanza = stanza_class()
                if defaults is None:
                    known_defaults = {
                        Message: ['type'],
                        Presence: ['priority']
                    }
                    defaults = known_defaults.get(stanza_class, [])
                for interface in defaults:
                    stanza[interface] = stanza[interface]
                    stanza2[interface] = stanza2[interface]
                    # Can really only automatically add defaults for top
                    # level attribute values. Anything else must be accounted
                    # for in the provided XML string.
                    if interface not in xml.attrib:
                        if interface in default_stanza.xml.attrib:
                            value = default_stanza.xml.attrib[interface]
                            xml.attrib[interface] = value

                values = stanza2.values
                stanza3 = stanza_class()
                stanza3.values = values

                debug = "Three methods for creating stanzas do not match.\n"
                debug += "Given XML:\n%s\n" % tostring(xml)
                debug += "Given stanza:\n%s\n" % tostring(stanza.xml)
                debug += "Generated stanza:\n%s\n" % tostring(stanza2.xml)
                debug += "Second generated stanza:\n%s\n" % tostring(stanza3.xml)
                result = self.compare(xml, stanza.xml, stanza2.xml, stanza3.xml)
            else:
                debug = "Two methods for creating stanzas do not match.\n"
                debug += "Given XML:\n%s\n" % tostring(xml)
                debug += "Given stanza:\n%s\n" % tostring(stanza.xml)
                debug += "Generated stanza:\n%s\n" % tostring(stanza2.xml)
                result = self.compare(xml, stanza.xml, stanza2.xml)

            self.failUnless(result, debug)

    # ------------------------------------------------------------------
    # Methods for simulating stanza streams.

    def stream_disconnect(self):
        """
        Simulate a stream disconnection.
        """
        if self.xmpp:
            self.xmpp.socket.disconnect_error()

    def stream_start(self, mode='client', skip=True, header=None,
                           socket='mock', jid='tester@localhost',
                           password='test', server='localhost',
                           port=5222, sasl_mech=None,
                           plugins=None, plugin_config={}):
        """
        Initialize an XMPP client or component using a dummy XML stream.

        Arguments:
            mode     -- Either 'client' or 'component'. Defaults to 'client'.
            skip     -- Indicates if the first item in the sent queue (the
                        stream header) should be removed. Tests that wish
                        to test initializing the stream should set this to
                        False. Otherwise, the default of True should be used.
            socket   -- Either 'mock' or 'live' to indicate if the socket
                        should be a dummy, mock socket or a live, functioning
                        socket. Defaults to 'mock'.
            jid      -- The JID to use for the connection.
                        Defaults to 'tester@localhost'.
            password -- The password to use for the connection.
                        Defaults to 'test'.
            server   -- The name of the XMPP server. Defaults to 'localhost'.
            port     -- The port to use when connecting to the server.
                        Defaults to 5222.
            plugins  -- List of plugins to register. By default, all plugins
                        are loaded.
        """
        if mode == 'client':
            self.xmpp = ClientXMPP(jid, password,
                                   sasl_mech=sasl_mech,
                                   plugin_config=plugin_config)
        elif mode == 'component':
            self.xmpp = ComponentXMPP(jid, password,
                                      server, port,
                                      plugin_config=plugin_config)
        else:
            raise ValueError("Unknown XMPP connection mode.")

        # Remove unique ID prefix to make it easier to test
        self.xmpp._id_prefix = ''
        self.xmpp._disconnect_wait_for_threads = False
        self.xmpp.default_lang = None
        self.xmpp.peer_default_lang = None

        # We will use this to wait for the session_start event
        # for live connections.
        skip_queue = Queue()

        if socket == 'mock':
            self.xmpp.set_socket(TestSocket())

            # Simulate connecting for mock sockets.
            self.xmpp.auto_reconnect = False
            self.xmpp.state._set_state('connected')

            # Must have the stream header ready for xmpp.process() to work.
            if not header:
                header = self.xmpp.stream_header
            self.xmpp.socket.recv_data(header)
        elif socket == 'live':
            self.xmpp.socket_class = TestLiveSocket

            def wait_for_session(x):
                self.xmpp.socket.clear()
                skip_queue.put('started')

            self.xmpp.add_event_handler('session_start', wait_for_session)
            if server is not None:
                self.xmpp.connect((server, port))
            else:
                self.xmpp.connect()
        else:
            raise ValueError("Unknown socket type.")

        if plugins is None:
            self.xmpp.register_plugins()
        else:
            for plugin in plugins:
                self.xmpp.register_plugin(plugin)

        # Some plugins require messages to have ID values. Set
        # this to True in tests related to those plugins.
        self.xmpp.use_message_ids = False

        self.xmpp.process(threaded=True)
        if skip:
            if socket != 'live':
                # Mark send queue as usable
                self.xmpp.session_started_event.set()
                # Clear startup stanzas
                self.xmpp.socket.next_sent(timeout=1)
                if mode == 'component':
                    self.xmpp.socket.next_sent(timeout=1)
            else:
                skip_queue.get(block=True, timeout=10)

    def make_header(self, sto='',
                          sfrom='',
                          sid='',
                          stream_ns="http://etherx.jabber.org/streams",
                          default_ns="jabber:client",
                          default_lang="en",
                          version="1.0",
                          xml_header=True):
        """
        Create a stream header to be received by the test XMPP agent.

        The header must be saved and passed to stream_start.

        Arguments:
            sto        -- The recipient of the stream header.
            sfrom      -- The agent sending the stream header.
            sid        -- The stream's id.
            stream_ns  -- The namespace of the stream's root element.
            default_ns -- The default stanza namespace.
            version    -- The stream version.
            xml_header -- Indicates if the XML version header should be
                          appended before the stream header.
        """
        header = '<stream:stream %s>'
        parts = []
        if xml_header:
            header = '<?xml version="1.0"?>' + header
        if sto:
            parts.append('to="%s"' % sto)
        if sfrom:
            parts.append('from="%s"' % sfrom)
        if sid:
            parts.append('id="%s"' % sid)
        if default_lang:
            parts.append('xml:lang="%s"' % default_lang)
        parts.append('version="%s"' % version)
        parts.append('xmlns:stream="%s"' % stream_ns)
        parts.append('xmlns="%s"' % default_ns)
        return header % ' '.join(parts)

    def recv(self, data, defaults=[], method='exact',
             use_values=True, timeout=1):
        """
        Pass data to the dummy XMPP client as if it came from an XMPP server.

        If using a live connection, verify what the server has sent.

        Arguments:
            data         -- If a dummy socket is being used, the XML that is to
                            be received next. Otherwise it is the criteria used
                            to match against live data that is received.
            defaults     -- A list of stanza interfaces with default values that
                            may interfere with comparisons.
            method       -- Select the type of comparison to use for
                            verifying the received stanza. Options are 'exact',
                            'id', 'stanzapath', 'xpath', and 'mask'.
                            Defaults to the value of self.match_method.
            use_values   -- Indicates if stanza comparisons should test using
                            stanza.values. Defaults to True.
            timeout      -- Time to wait in seconds for data to be received by
                            a live connection.
        """
        if self.xmpp.socket.is_live:
            # we are working with a live connection, so we should
            # verify what has been received instead of simulating
            # receiving data.
            recv_data = self.xmpp.socket.next_recv(timeout)
            if recv_data is None:
                self.fail("No stanza was received.")
            xml = self.parse_xml(recv_data)
            self.fix_namespaces(xml, 'jabber:client')
            stanza = self.xmpp._build_stanza(xml, 'jabber:client')
            self.check(stanza, data,
                       method=method,
                       defaults=defaults,
                       use_values=use_values)
        else:
            # place the data in the dummy socket receiving queue.
            data = str(data)
            self.xmpp.socket.recv_data(data)

    def recv_header(self, sto='',
                          sfrom='',
                          sid='',
                          stream_ns="http://etherx.jabber.org/streams",
                          default_ns="jabber:client",
                          version="1.0",
                          xml_header=False,
                          timeout=1):
        """
        Check that a given stream header was received.

        Arguments:
            sto        -- The recipient of the stream header.
            sfrom      -- The agent sending the stream header.
            sid        -- The stream's id. Set to None to ignore.
            stream_ns  -- The namespace of the stream's root element.
            default_ns -- The default stanza namespace.
            version    -- The stream version.
            xml_header -- Indicates if the XML version header should be
                          appended before the stream header.
            timeout    -- Length of time to wait in seconds for a
                          response.
        """
        header = self.make_header(sto, sfrom, sid,
                                  stream_ns=stream_ns,
                                  default_ns=default_ns,
                                  version=version,
                                  xml_header=xml_header)
        recv_header = self.xmpp.socket.next_recv(timeout)
        if recv_header is None:
            raise ValueError("Socket did not return data.")

        # Apply closing elements so that we can construct
        # XML objects for comparison.
        header2 = header + '</stream:stream>'
        recv_header2 = recv_header + '</stream:stream>'

        xml = self.parse_xml(header2)
        recv_xml = self.parse_xml(recv_header2)

        if sid is None:
            # Ignore the id sent by the server since
            # we can't know in advance what it will be.
            if 'id' in recv_xml.attrib:
                del recv_xml.attrib['id']

        # Ignore the xml:lang attribute for now.
        if 'xml:lang' in recv_xml.attrib:
            del recv_xml.attrib['xml:lang']
        xml_ns = 'http://www.w3.org/XML/1998/namespace'
        if '{%s}lang' % xml_ns in recv_xml.attrib:
            del recv_xml.attrib['{%s}lang' % xml_ns]

        if list(recv_xml):
            # We received more than just the header
            for xml in recv_xml:
                self.xmpp.socket.recv_data(tostring(xml))

            attrib = recv_xml.attrib
            recv_xml.clear()
            recv_xml.attrib = attrib

        self.failUnless(
            self.compare(xml, recv_xml),
            "Stream headers do not match:\nDesired:\n%s\nReceived:\n%s" % (
                '%s %s' % (xml.tag, xml.attrib),
                '%s %s' % (recv_xml.tag, recv_xml.attrib)))

    def recv_feature(self, data, method='mask', use_values=True, timeout=1):
        """
        """
        if method is None and hasattr(self, 'match_method'):
            method = getattr(self, 'match_method')

        if self.xmpp.socket.is_live:
            # we are working with a live connection, so we should
            # verify what has been received instead of simulating
            # receiving data.
            recv_data = self.xmpp.socket.next_recv(timeout)
            xml = self.parse_xml(data)
            recv_xml = self.parse_xml(recv_data)
            if recv_data is None:
                self.fail("No stanza was received.")
            if method == 'exact':
                self.failUnless(self.compare(xml, recv_xml),
                    "Features do not match.\nDesired:\n%s\nReceived:\n%s" % (
                        tostring(xml), tostring(recv_xml)))
            elif method == 'mask':
                matcher = MatchXMLMask(xml)
                self.failUnless(matcher.match(recv_xml),
                    "Stanza did not match using %s method:\n" % method + \
                    "Criteria:\n%s\n" % tostring(xml) + \
                    "Stanza:\n%s" % tostring(recv_xml))
            else:
                raise ValueError("Uknown matching method: %s" % method)
        else:
            # place the data in the dummy socket receiving queue.
            data = str(data)
            self.xmpp.socket.recv_data(data)

    def send_header(self, sto='',
                          sfrom='',
                          sid='',
                          stream_ns="http://etherx.jabber.org/streams",
                          default_ns="jabber:client",
                          default_lang="en",
                          version="1.0",
                          xml_header=False,
                          timeout=1):
        """
        Check that a given stream header was sent.

        Arguments:
            sto        -- The recipient of the stream header.
            sfrom      -- The agent sending the stream header.
            sid        -- The stream's id.
            stream_ns  -- The namespace of the stream's root element.
            default_ns -- The default stanza namespace.
            version    -- The stream version.
            xml_header -- Indicates if the XML version header should be
                          appended before the stream header.
            timeout    -- Length of time to wait in seconds for a
                          response.
        """
        header = self.make_header(sto, sfrom, sid,
                                  stream_ns=stream_ns,
                                  default_ns=default_ns,
                                  default_lang=default_lang,
                                  version=version,
                                  xml_header=xml_header)
        sent_header = self.xmpp.socket.next_sent(timeout)
        if sent_header is None:
            raise ValueError("Socket did not return data.")

        # Apply closing elements so that we can construct
        # XML objects for comparison.
        header2 = header + '</stream:stream>'
        sent_header2 = sent_header + b'</stream:stream>'

        xml = self.parse_xml(header2)
        sent_xml = self.parse_xml(sent_header2)

        self.failUnless(
            self.compare(xml, sent_xml),
            "Stream headers do not match:\nDesired:\n%s\nSent:\n%s" % (
                header, sent_header))

    def send_feature(self, data, method='mask', use_values=True, timeout=1):
        """
        """
        sent_data = self.xmpp.socket.next_sent(timeout)
        xml = self.parse_xml(data)
        sent_xml = self.parse_xml(sent_data)
        if sent_data is None:
            self.fail("No stanza was sent.")
        if method == 'exact':
            self.failUnless(self.compare(xml, sent_xml),
                "Features do not match.\nDesired:\n%s\nReceived:\n%s" % (
                    tostring(xml), tostring(sent_xml)))
        elif method == 'mask':
            matcher = MatchXMLMask(xml)
            self.failUnless(matcher.match(sent_xml),
                "Stanza did not match using %s method:\n" % method + \
                "Criteria:\n%s\n" % tostring(xml) + \
                "Stanza:\n%s" % tostring(sent_xml))
        else:
            raise ValueError("Uknown matching method: %s" % method)

    def send(self, data, defaults=None, use_values=True,
             timeout=.5, method='exact'):
        """
        Check that the XMPP client sent the given stanza XML.

        Extracts the next sent stanza and compares it with the given
        XML using check.

        Arguments:
            stanza_class -- The class of the sent stanza object.
            data         -- The XML string of the expected Message stanza,
                            or an equivalent stanza object.
            use_values   -- Modifies the type of tests used by check_message.
            defaults     -- A list of stanza interfaces that have defaults
                            values which may interfere with comparisons.
            timeout      -- Time in seconds to wait for a stanza before
                            failing the check.
            method       -- Select the type of comparison to use for
                            verifying the sent stanza. Options are 'exact',
                            'id', 'stanzapath', 'xpath', and 'mask'.
                            Defaults to the value of self.match_method.
        """
        sent = self.xmpp.socket.next_sent(timeout)
        if data is None and sent is None:
            return
        if data is None and sent is not None:
            self.fail("Stanza data was sent: %s" % sent)
        if sent is None:
            self.fail("No stanza was sent.")

        xml = self.parse_xml(sent)
        self.fix_namespaces(xml, 'jabber:client')
        sent = self.xmpp._build_stanza(xml, 'jabber:client')
        self.check(sent, data,
                   method=method,
                   defaults=defaults,
                   use_values=use_values)

    def stream_close(self):
        """
        Disconnect the dummy XMPP client.

        Can be safely called even if stream_start has not been called.

        Must be placed in the tearDown method of a test class to ensure
        that the XMPP client is disconnected after an error.
        """
        if hasattr(self, 'xmpp') and self.xmpp is not None:
            self.xmpp.socket.recv_data(self.xmpp.stream_footer)
            self.xmpp.disconnect()

    # ------------------------------------------------------------------
    # XML Comparison and Cleanup

    def fix_namespaces(self, xml, ns):
        """
        Assign a namespace to an element and any children that
        don't have a namespace.

        Arguments:
            xml -- The XML object to fix.
            ns  -- The namespace to add to the XML object.
        """
        if xml.tag.startswith('{'):
            return
        xml.tag = '{%s}%s' % (ns, xml.tag)
        for child in xml:
            self.fix_namespaces(child, ns)

    def compare(self, xml, *other):
        """
        Compare XML objects.

        Arguments:
            xml    -- The XML object to compare against.
            *other -- The list of XML objects to compare.
        """
        if not other:
            return False

        # Compare multiple objects
        if len(other) > 1:
            for xml2 in other:
                if not self.compare(xml, xml2):
                    return False
            return True

        other = other[0]

        # Step 1: Check tags
        if xml.tag != other.tag:
            return False

        # Step 2: Check attributes
        if xml.attrib != other.attrib:
            return False

        # Step 3: Check text
        if xml.text is None:
            xml.text = ""
        if other.text is None:
            other.text = ""
        xml.text = xml.text.strip()
        other.text = other.text.strip()

        if xml.text != other.text:
            return False

        # Step 4: Check children count
        if len(list(xml)) != len(list(other)):
            return False

        # Step 5: Recursively check children
        for child in xml:
            child2s = other.findall("%s" % child.tag)
            if child2s is None:
                return False
            for child2 in child2s:
                if self.compare(child, child2):
                    break
            else:
                return False

        # Step 6: Recursively check children the other way.
        for child in other:
            child2s = xml.findall("%s" % child.tag)
            if child2s is None:
                return False
            for child2 in child2s:
                if self.compare(child, child2):
                    break
            else:
                return False

        # Everything matches
        return True

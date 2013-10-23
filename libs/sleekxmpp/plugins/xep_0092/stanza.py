"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET


class Version(ElementBase):

    """
    XMPP allows for an agent to advertise the name and version of the
    underlying software libraries, as well as the operating system
    that the agent is running on.

    Example version stanzas:
      <iq type="get">
        <query xmlns="jabber:iq:version" />
      </iq>

      <iq type="result">
        <query xmlns="jabber:iq:version">
          <name>SleekXMPP</name>
          <version>1.0</version>
          <os>Linux</os>
        </query>
      </iq>

    Stanza Interface:
        name    -- The human readable name of the software.
        version -- The specific version of the software.
        os      -- The name of the operating system running the program.
    """

    name = 'query'
    namespace = 'jabber:iq:version'
    plugin_attrib = 'software_version'
    interfaces = set(('name', 'version', 'os'))
    sub_interfaces = interfaces

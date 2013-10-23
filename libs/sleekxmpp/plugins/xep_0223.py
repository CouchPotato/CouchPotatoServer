"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins.base import BasePlugin, register_plugin


log = logging.getLogger(__name__)


class XEP_0223(BasePlugin):

    """
    XEP-0223: Persistent Storage of Private Data via PubSub
    """

    name = 'xep_0223'
    description = 'XEP-0223: Persistent Storage of Private Data via PubSub'
    dependencies = set(['xep_0163', 'xep_0060', 'xep_0004'])

    profile = {'pubsub#persist_items': True,
               'pubsub#send_last_published_item': 'never'}

    def configure(self, node):
        """
        Update a node's configuration to match the public storage profile.
        """
        config = self.xmpp['xep_0004'].Form()
        config['type'] = 'submit'

        for field, value in self.profile.items():
            config.add_field(var=field, value=value)

        return self.xmpp['xep_0060'].set_node_config(None, node, config,
                ifrom=ifrom,
                block=block,
                callback=callback,
                timeout=timeout)

    def store(self, stanza, node=None, id=None, ifrom=None, options=None,
              block=True, callback=None, timeout=None):
        """
        Store private data via PEP.

        This is just a (very) thin wrapper around the XEP-0060 publish()
        method to set the defaults expected by PEP.

        Arguments:
            stanza   -- The private content to store.
            node     -- The node to publish the content to. If not specified,
                        the stanza's namespace will be used.
            id       -- Optionally specify the ID of the item.
            options  -- Publish options to use, which will be modified to
                        fit the persistent storage option profile.
            ifrom    -- Specify the sender's JID.
            block    -- Specify if the send call will block until a response
                        is received, or a timeout occurs. Defaults to True.
            timeout  -- The length of time (in seconds) to wait for a response
                        before exiting the send call if blocking is used.
                        Defaults to sleekxmpp.xmlstream.RESPONSE_TIMEOUT
            callback -- Optional reference to a stream handler function. Will
                        be executed when a reply stanza is received.
        """
        if not options:
            options = self.xmpp['xep_0004'].stanza.Form()
            options['type'] = 'submit'
            options.add_field(
                var='FORM_TYPE',
                ftype='hidden',
                value='http://jabber.org/protocol/pubsub#publish-options')

        for field, value in self.profile.items():
            if field not in options.fields:
                options.add_field(var=field)
            options.fields[field]['value'] = value

        return self.xmpp['xep_0163'].publish(stanza, node,
                options=options,
                ifrom=ifrom,
                block=block,
                callback=callback,
                timeout=timeout)

    def retrieve(self, node, id=None, item_ids=None, ifrom=None,
                 block=True, callback=None, timeout=None):
        """
        Retrieve private data via PEP.

        This is just a (very) thin wrapper around the XEP-0060 publish()
        method to set the defaults expected by PEP.

        Arguments:
            node     -- The node to retrieve content from.
            id       -- Optionally specify the ID of the item.
            item_ids -- Specify a group of IDs. If id is also specified, it
                        will be included in item_ids.
            ifrom    -- Specify the sender's JID.
            block    -- Specify if the send call will block until a response
                        is received, or a timeout occurs. Defaults to True.
            timeout  -- The length of time (in seconds) to wait for a response
                        before exiting the send call if blocking is used.
                        Defaults to sleekxmpp.xmlstream.RESPONSE_TIMEOUT
            callback -- Optional reference to a stream handler function. Will
                        be executed when a reply stanza is received.
        """
        if item_ids is None:
            item_ids = []
        if id is not None:
            item_ids.append(id)

        return self.xmpp['xep_0060'].get_items(None, node,
                item_ids=item_ids,
                ifrom=ifrom,
                block=block,
                callback=callback,
                timeout=timeout)


register_plugin(XEP_0223)

"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz, Erik Reuterborg Larsson
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

import sleekxmpp
from sleekxmpp import Iq
from sleekxmpp.plugins import BasePlugin, register_plugin
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins.xep_0059 import stanza, Set
from sleekxmpp.exceptions import XMPPError


log = logging.getLogger(__name__)


class ResultIterator():

    """
    An iterator for Result Set Managment
    """

    def __init__(self, query, interface, results='substanzas', amount=10,
                       start=None, reverse=False):
        """
        Arguments:
           query     -- The template query
           interface -- The substanza of the query, for example disco_items
           results   -- The query stanza's interface which provides a
                        countable list of query results.
           amount    -- The max amounts of items to request per iteration
           start     -- From which item id to start
           reverse   -- If True, page backwards through the results

        Example:
           q = Iq()
           q['to'] = 'pubsub.example.com'
           q['disco_items']['node'] = 'blog'
           for i in ResultIterator(q, 'disco_items', '10'):
               print i['disco_items']['items']

        """
        self.query = query
        self.amount = amount
        self.start = start
        self.interface = interface
        self.results = results
        self.reverse = reverse
        self._stop = False

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        """
        Return the next page of results from a query.

        Note: If using backwards paging, then the next page of
              results will be the items before the current page
              of items.
        """
        if self._stop:
            raise StopIteration
        self.query[self.interface]['rsm']['before'] = self.reverse
        self.query['id'] = self.query.stream.new_id()
        self.query[self.interface]['rsm']['max'] = str(self.amount)

        if self.start and self.reverse:
            self.query[self.interface]['rsm']['before'] = self.start
        elif self.start:
            self.query[self.interface]['rsm']['after'] = self.start

        try:
            r = self.query.send(block=True)

            if not r[self.interface]['rsm']['first'] and \
               not r[self.interface]['rsm']['last']:
                raise StopIteration

            if r[self.interface]['rsm']['count'] and \
               r[self.interface]['rsm']['first_index']:
                count = int(r[self.interface]['rsm']['count'])
                first = int(r[self.interface]['rsm']['first_index'])
                num_items = len(r[self.interface][self.results])
                if first + num_items == count:
                    self._stop = True

            if self.reverse:
                self.start = r[self.interface]['rsm']['first']
            else:
                self.start = r[self.interface]['rsm']['last']

            return r
        except XMPPError:
            raise StopIteration


class XEP_0059(BasePlugin):

    """
    XEP-0050: Result Set Management
    """

    name = 'xep_0059'
    description = 'XEP-0059: Result Set Management'
    dependencies = set(['xep_0030'])
    stanza = stanza

    def plugin_init(self):
        """
        Start the XEP-0059 plugin.
        """
        register_stanza_plugin(self.xmpp['xep_0030'].stanza.DiscoItems,
                               self.stanza.Set)

    def plugin_end(self):
        self.xmpp['xep_0030'].del_feature(feature=Set.namespace)

    def session_bind(self, jid):
        self.xmpp['xep_0030'].add_feature(Set.namespace)

    def iterate(self, stanza, interface, results='substanzas'):
        """
        Create a new result set iterator for a given stanza query.

        Arguments:
            stanza    -- A stanza object to serve as a template for
                         queries made each iteration. For example, a
                         basic disco#items query.
            interface -- The name of the substanza to which the
                         result set management stanza should be
                         appended. For example, for disco#items queries
                         the interface 'disco_items' should be used.
            results   -- The name of the interface containing the
                         query results (typically just 'substanzas').
        """
        return ResultIterator(stanza, interface, results)

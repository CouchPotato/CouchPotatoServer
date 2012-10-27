#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2011 Nicolas Wack <wackou@gmail.com>
#
# GuessIt is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# GuessIt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import unicode_literals
from guessit import UnicodeMixin, base_text_type, Guess
from guessit.textutils import clean_string, str_fill
from guessit.patterns import group_delimiters
import logging

log = logging.getLogger(__name__)


class BaseMatchTree(UnicodeMixin):
    """A MatchTree represents the hierarchical split of a string into its
    constituent semantic groups."""

    def __init__(self, string='', span=None, parent=None):
        self.string = string
        self.span = span or (0, len(string))
        self.parent = parent
        self.children = []
        self.guess = Guess()

    @property
    def value(self):
        return self.string[self.span[0]:self.span[1]]

    @property
    def clean_value(self):
        return clean_string(self.value)

    @property
    def offset(self):
        return self.span[0]

    @property
    def info(self):
        result = dict(self.guess)

        for c in self.children:
            result.update(c.info)

        return result

    @property
    def root(self):
        if not self.parent:
            return self

        return self.parent.root

    @property
    def depth(self):
        if self.is_leaf():
            return 0

        return 1 + max(c.depth for c in self.children)

    def is_leaf(self):
        return self.children == []

    def add_child(self, span):
        child = MatchTree(self.string, span=span, parent=self)
        self.children.append(child)

    def partition(self, indices):
        indices = sorted(indices)
        if indices[0] != 0:
            indices.insert(0, 0)
        if indices[-1] != len(self.value):
            indices.append(len(self.value))

        for start, end in zip(indices[:-1], indices[1:]):
            self.add_child(span=(self.offset + start,
                                 self.offset + end))

    def split_on_components(self, components):
        offset = 0
        for c in components:
            start = self.value.find(c, offset)
            end = start + len(c)
            self.add_child(span=(self.offset + start,
                                 self.offset + end))
            offset = end

    def nodes_at_depth(self, depth):
        if depth == 0:
            yield self

        for child in self.children:
            for node in child.nodes_at_depth(depth - 1):
                yield node

    @property
    def node_idx(self):
        if self.parent is None:
            return ()
        return self.parent.node_idx + (self.parent.children.index(self),)

    def node_at(self, idx):
        if not idx:
            return self

        try:
            return self.children[idx[0]].node_at(idx[1:])
        except:
            raise ValueError('Non-existent node index: %s' % (idx,))

    def nodes(self):
        yield self
        for child in self.children:
            for node in child.nodes():
                yield node

    def _leaves(self):
        if self.is_leaf():
            yield self
        else:
            for child in self.children:
                # pylint: disable=W0212
                for leaf in child._leaves():
                    yield leaf

    def leaves(self):
        return list(self._leaves())

    def to_string(self):
        empty_line = ' ' * len(self.string)

        def to_hex(x):
            if isinstance(x, int):
                return str(x) if x < 10 else chr(55 + x)
            return x

        def meaning(result):
            mmap = { 'episodeNumber': 'E',
                     'season': 'S',
                     'extension': 'e',
                     'format': 'f',
                     'language': 'l',
                     'country': 'C',
                     'videoCodec': 'v',
                     'audioCodec': 'a',
                     'website': 'w',
                     'container': 'c',
                     'series': 'T',
                     'title': 't',
                     'date': 'd',
                     'year': 'y',
                     'releaseGroup': 'r',
                     'screenSize': 's'
                     }

            if result is None:
                return ' '

            for prop, l in mmap.items():
                if prop in result:
                    return l

            return 'x'

        lines = [ empty_line ] * (self.depth + 2) # +2: remaining, meaning
        lines[-2] = self.string

        for node in self.nodes():
            if node == self:
                continue

            idx = node.node_idx
            depth = len(idx) - 1
            if idx:
                lines[depth] = str_fill(lines[depth], node.span,
                                        to_hex(idx[-1]))
            if node.guess:
                lines[-2] = str_fill(lines[-2], node.span, '_')
                lines[-1] = str_fill(lines[-1], node.span, meaning(node.guess))

        lines.append(self.string)

        return '\n'.join(lines)

    def __unicode__(self):
        return self.to_string()


class MatchTree(BaseMatchTree):
    """The MatchTree contains a few "utility" methods which are not necessary
    for the BaseMatchTree, but add a lot of convenience for writing
    higher-level rules."""

    def _unidentified_leaves(self,
                             valid=lambda leaf: len(leaf.clean_value) >= 2):
        for leaf in self._leaves():
            if not leaf.guess and valid(leaf):
                yield leaf

    def unidentified_leaves(self,
                            valid=lambda leaf: len(leaf.clean_value) >= 2):
        return list(self._unidentified_leaves(valid))

    def _leaves_containing(self, property_name):
        if isinstance(property_name, base_text_type):
            property_name = [ property_name ]

        for leaf in self._leaves():
            for prop in property_name:
                if prop in leaf.guess:
                    yield leaf
                    break

    def leaves_containing(self, property_name):
        return list(self._leaves_containing(property_name))

    def first_leaf_containing(self, property_name):
        try:
            return next(self._leaves_containing(property_name))
        except StopIteration:
            return None

    def _previous_unidentified_leaves(self, node):
        node_idx = node.node_idx
        for leaf in self._unidentified_leaves():
            if leaf.node_idx < node_idx:
                yield leaf

    def previous_unidentified_leaves(self, node):
        return list(self._previous_unidentified_leaves(node))

    def _previous_leaves_containing(self, node, property_name):
        node_idx = node.node_idx
        for leaf in self._leaves_containing(property_name):
            if leaf.node_idx < node_idx:
                yield leaf

    def previous_leaves_containing(self, node, property_name):
        return list(self._previous_leaves_containing(node, property_name))

    def is_explicit(self):
        """Return whether the group was explicitly enclosed by
        parentheses/square brackets/etc."""
        return (self.value[0] + self.value[-1]) in group_delimiters

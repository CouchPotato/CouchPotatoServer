#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Smewt - A smart collection manager
# Copyright (c) 2008 Nicolas Wack <wackou@gmail.com>
#
# Smewt is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Smewt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import unicode_literals
from guessit import s
from guessit.patterns import sep
import functools
import unicodedata
import copy

# string-related functions


def strip_brackets(s):
    if not s:
        return s

    if ((s[0] == '[' and s[-1] == ']') or
        (s[0] == '(' and s[-1] == ')') or
        (s[0] == '{' and s[-1] == '}')):
        return s[1:-1]

    return s


def clean_string(s):
    for c in sep[:-2]: # do not remove dashes ('-')
        s = s.replace(c, ' ')
    parts = s.split()
    result = ' '.join(p for p in parts if p != '')

    # now also remove dashes on the outer part of the string
    while result and result[0] in sep:
        result = result[1:]
    while result and result[-1] in sep:
        result = result[:-1]

    return result


def str_replace(string, pos, c):
    return string[:pos] + c + string[pos+1:]


def str_fill(string, region, c):
    start, end = region
    return string[:start] + c * (end - start) + string[end:]



def levenshtein(a, b):
    if not a:
        return len(b)
    if not b:
        return len(a)

    m = len(a)
    n = len(b)
    d = []
    for i in range(m+1):
        d.append([0] * (n+1))

    for i in range(m+1):
        d[i][0] = i

    for j in range(n+1):
        d[0][j] = j

    for i in range(1, m+1):
        for j in range(1, n+1):
            if a[i-1] == b[j-1]:
                cost = 0
            else:
                cost = 1

            d[i][j] = min(d[i-1][j] + 1,     # deletion
                          d[i][j-1] + 1,     # insertion
                          d[i-1][j-1] + cost # substitution
                          )

    return d[m][n]


# group-related functions

def find_first_level_groups_span(string, enclosing):
    """Return a list of pairs (start, end) for the groups delimited by the given
    enclosing characters.
    This does not return nested groups, ie: '(ab(c)(d))' will return a single group
    containing the whole string.

    >>> find_first_level_groups_span('abcd', '()')
    []

    >>> find_first_level_groups_span('abc(de)fgh', '()')
    [(3, 7)]

    >>> find_first_level_groups_span('(ab(c)(d))', '()')
    [(0, 10)]

    >>> find_first_level_groups_span('ab[c]de[f]gh(i)', '[]')
    [(2, 5), (7, 10)]
    """
    opening, closing = enclosing
    depth = [] # depth is a stack of indices where we opened a group
    result = []
    for i, c, in enumerate(string):
        if c == opening:
            depth.append(i)
        elif c == closing:
            try:
                start = depth.pop()
                end = i
                if not depth:
                    # we emptied our stack, so we have a 1st level group
                    result.append((start, end+1))
            except IndexError:
                # we closed a group which was not opened before
                pass

    return result


def split_on_groups(string, groups):
    """Split the given string using the different known groups for boundaries.
    >>> s(split_on_groups('0123456789', [ (2, 4) ]))
    ['01', '23', '456789']

    >>> s(split_on_groups('0123456789', [ (2, 4), (4, 6) ]))
    ['01', '23', '45', '6789']

    >>> s(split_on_groups('0123456789', [ (5, 7), (2, 4) ]))
    ['01', '23', '4', '56', '789']

    """
    if not groups:
        return [ string ]

    boundaries = sorted(set(functools.reduce(lambda l, x: l + list(x), groups, [])))
    if boundaries[0] != 0:
        boundaries.insert(0, 0)
    if boundaries[-1] != len(string):
        boundaries.append(len(string))

    groups = [ string[start:end] for start, end in zip(boundaries[:-1],
                                                       boundaries[1:]) ]

    return [ g for g in groups if g ] # return only non-empty groups


def find_first_level_groups(string, enclosing, blank_sep=None):
    """Return a list of groups that could be split because of explicit grouping.
    The groups are delimited by the given enclosing characters.

    You can also specify if you want to blank the separator chars in the returned
    list of groups by specifying a character for it. None means it won't be replaced.

    This does not return nested groups, ie: '(ab(c)(d))' will return a single group
    containing the whole string.

    >>> s(find_first_level_groups('', '()'))
    ['']

    >>> s(find_first_level_groups('abcd', '()'))
    ['abcd']

    >>> s(find_first_level_groups('abc(de)fgh', '()'))
    ['abc', '(de)', 'fgh']

    >>> s(find_first_level_groups('(ab(c)(d))', '()', blank_sep = '_'))
    ['_ab(c)(d)_']

    >>> s(find_first_level_groups('ab[c]de[f]gh(i)', '[]'))
    ['ab', '[c]', 'de', '[f]', 'gh(i)']

    >>> s(find_first_level_groups('()[]()', '()', blank_sep = '-'))
    ['--', '[]', '--']

    """
    groups = find_first_level_groups_span(string, enclosing)
    if blank_sep:
        for start, end in groups:
            string = str_replace(string, start, blank_sep)
            string = str_replace(string, end-1, blank_sep)

    return split_on_groups(string, groups)

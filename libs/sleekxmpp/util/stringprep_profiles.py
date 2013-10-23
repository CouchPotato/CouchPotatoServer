# -*- coding: utf-8 -*-
"""
    sleekxmpp.util.stringprep_profiles
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module makes it easier to define profiles of stringprep,
    such as nodeprep and resourceprep for JID validation, and
    SASLprep for SASL.

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2012 Nathanael C. Fritz, Lance J.T. Stout
    :license: MIT, see LICENSE for more details
"""


from __future__ import unicode_literals

import sys
import stringprep
import unicodedata

from sleekxmpp.util import unicode


class StringPrepError(UnicodeError):
    pass


def b1_mapping(char):
    """Map characters that are commonly mapped to nothing."""
    return '' if stringprep.in_table_b1(char) else None


def c12_mapping(char):
    """Map non-ASCII whitespace to spaces."""
    return ' ' if stringprep.in_table_c12(char) else None


def map_input(data, tables=None):
    """
    Each character in the input stream MUST be checked against
    a mapping table.
    """
    result = []
    for char in data:
        replacement = None

        for mapping in tables:
            replacement = mapping(char)
            if replacement is not None:
                break

        if replacement is None:
            replacement = char
        result.append(replacement)
    return ''.join(result)


def normalize(data, nfkc=True):
    """
    A profile can specify one of two options for Unicode normalization:
        - no normalization
        - Unicode normalization with form KC
    """
    if nfkc:
        data = unicodedata.normalize('NFKC', data)
    return data


def prohibit_output(data, tables=None):
    """
    Before the text can be emitted, it MUST be checked for prohibited
    code points.
    """
    for char in data:
        for check in tables:
            if check(char):
                raise StringPrepError("Prohibited code point: %s" % char)


def check_bidi(data):
    """
    1) The characters in section 5.8 MUST be prohibited.

    2) If a string contains any RandALCat character, the string MUST NOT
       contain any LCat character.

    3) If a string contains any RandALCat character, a RandALCat
       character MUST be the first character of the string, and a
       RandALCat character MUST be the last character of the string.
    """
    if not data:
        return data

    has_lcat = False
    has_randal = False

    for c in data:
        if stringprep.in_table_c8(c):
            raise StringPrepError("BIDI violation: seciton 6 (1)")
        if stringprep.in_table_d1(c):
            has_randal = True
        elif stringprep.in_table_d2(c):
            has_lcat = True

    if has_randal and has_lcat:
        raise StringPrepError("BIDI violation: section 6 (2)")

    first_randal = stringprep.in_table_d1(data[0])
    last_randal = stringprep.in_table_d1(data[-1])
    if has_randal and not (first_randal and last_randal):
        raise StringPrepError("BIDI violation: section 6 (3)")


def create(nfkc=True, bidi=True, mappings=None,
           prohibited=None, unassigned=None):
    """Create a profile of stringprep.

    :param bool nfkc:
        If `True`, perform NFKC Unicode normalization. Defaults to `True`.
    :param bool bidi:
        If `True`, perform bidirectional text checks. Defaults to `True`.
    :param list mappings:
        Optional list of functions for mapping characters to
        suitable replacements.
    :param list prohibited:
        Optional list of functions which check for the presence of
        prohibited characters.
    :param list unassigned:
        Optional list of functions for detecting the use of unassigned
        code points.

    :raises: StringPrepError
    :return: Unicode string of the resulting text passing the
             profile's requirements.
    """
    def profile(data, query=False):
        try:
            data = unicode(data)
        except UnicodeError:
            raise StringPrepError

        data = map_input(data, mappings)
        data = normalize(data, nfkc)
        prohibit_output(data, prohibited)
        if bidi:
            check_bidi(data)
        if query and unassigned:
            check_unassigned(data, unassigned)
        return data
    return profile

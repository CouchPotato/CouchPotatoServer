#!/usr/bin/env python

# Copyright (c) 2004-2009 Zooko "Zooko" Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

import unittest

from pyutil.assertutil import _assert
from pyutil import strutil

class Teststrutil(unittest.TestCase):
    def test_short_input(self):
        self.failUnless(strutil.pop_trailing_newlines("\r\n") == "")
        self.failUnless(strutil.pop_trailing_newlines("\r") == "")
        self.failUnless(strutil.pop_trailing_newlines("x\r\n") == "x")
        self.failUnless(strutil.pop_trailing_newlines("x\r") == "x")

    def test_split(self):
        _assert(strutil.split_on_newlines("x\r\ny") == ["x", "y",], strutil.split_on_newlines("x\r\ny"))
        _assert(strutil.split_on_newlines("x\r\ny\r\n") == ["x", "y", '',], strutil.split_on_newlines("x\r\ny\r\n"))
        _assert(strutil.split_on_newlines("x\n\ny\n\n") == ["x", '', "y", '', '',], strutil.split_on_newlines("x\n\ny\n\n"))

    def test_commonprefix(self):
        _assert(strutil.commonprefix(["foo","foobarooo", "foosplat",]) == 'foo', strutil.commonprefix(["foo","foobarooo", "foosplat",]))
        _assert(strutil.commonprefix(["foo","afoobarooo", "foosplat",]) == '', strutil.commonprefix(["foo","afoobarooo", "foosplat",]))

    def test_commonsuffix(self):
        _assert(strutil.commonsuffix(["foo","foobarooo", "foosplat",]) == '', strutil.commonsuffix(["foo","foobarooo", "foosplat",]))
        _assert(strutil.commonsuffix(["foo","foobarooo", "foosplato",]) == 'o', strutil.commonsuffix(["foo","foobarooo", "foosplato",]))
        _assert(strutil.commonsuffix(["foo","foobarooofoo", "foosplatofoo",]) == 'foo', strutil.commonsuffix(["foo","foobarooofoo", "foosplatofoo",]))

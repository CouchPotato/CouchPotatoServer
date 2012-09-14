#!/usr/bin/env python

#  Copyright (c) 2002-2009 Zooko Wilcox-O'Hearn
#  portions Copyright (c) 2001 Autonomous Zone Industries
#  This file is part of pyutil; see README.rst for licensing terms.

# Python Standard Library modules
import unittest

from pyutil import assertutil

class Testy(unittest.TestCase):
    def test_bad_precond(self):
        adict=23
        try:
            assertutil.precondition(isinstance(adict, dict), "adict is required to be a dict.", 23, adict=adict, foo=None)
        except AssertionError, le:
            self.failUnless(le.args[0] == "precondition: 'adict is required to be a dict.' <type 'str'>, 23 <type 'int'>, foo: None <type 'NoneType'>, 'adict': 23 <type 'int'>")

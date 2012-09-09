#!/usr/bin/env python

import unittest

from decimal import Decimal

from pyutil import jsonutil

zero_point_one = Decimal("0.1")
class TestDecimal(unittest.TestCase):
    def test_encode(self):
        self.failUnlessEqual(jsonutil.dumps(zero_point_one), "0.1")

    def test_decode(self):
        self.failUnlessEqual(jsonutil.loads("0.1"), zero_point_one)

    def test_no_exception_on_convergent_parse_float(self):
        self.failUnlessEqual(jsonutil.loads("0.1", parse_float=Decimal), zero_point_one)

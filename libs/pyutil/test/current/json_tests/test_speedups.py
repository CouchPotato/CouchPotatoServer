from twisted.trial.unittest import SkipTest, TestCase

from pyutil.jsonutil import decoder
from pyutil.jsonutil import encoder

class TestSpeedups(TestCase):
    def test_scanstring(self):
        if not encoder.c_encode_basestring_ascii:
            raise SkipTest("no C extension speedups available to test")
        self.assertEquals(decoder.scanstring.__module__, "simplejson._speedups")
        self.assert_(decoder.scanstring is decoder.c_scanstring)

    def test_encode_basestring_ascii(self):
        if not encoder.c_encode_basestring_ascii:
            raise SkipTest("no C extension speedups available to test")
        self.assertEquals(encoder.encode_basestring_ascii.__module__, "simplejson._speedups")
        self.assert_(encoder.encode_basestring_ascii is
                          encoder.c_encode_basestring_ascii)

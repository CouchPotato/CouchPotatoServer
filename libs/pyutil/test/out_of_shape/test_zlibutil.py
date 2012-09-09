#!/usr/bin/env python

import unittest

from pyutil import randutil

from pyutil import zlibutil

class Accumulator:
    def __init__(self):
        self.buf = ''

    def write(self, str):
        self.buf += str

def make_decomp(realdecomp):
    def decomp(str, maxlen, maxmem):
        d = Accumulator()
        realdecomp(str, d, maxlen, maxmem)
        return d.buf
    return decomp

def genrandstr(strlen):
    return randutil.insecurerandstr(strlen)

def genbombstr(strlen):
    return '0' * strlen

MAXMEM=65*2**20

class ZlibTestCase(unittest.TestCase):
    def _help_test(self, genstring, decomp, strlen):
        s = genstring(strlen)
        cs = zlibutil.zlib.compress(s)
        s2 = decomp(cs, maxlen=strlen, maxmem=strlen*2**3 + zlibutil.MINMAXMEM)
        self.failUnless(s == s2)
        s2 = decomp(cs, maxlen=strlen, maxmem=strlen*2**6 + zlibutil.MINMAXMEM)
        self.failUnless(s == s2)
        self.failUnlessRaises(zlibutil.TooBigError, decomp, cs, maxlen=strlen-1, maxmem=strlen*2**3 + zlibutil.MINMAXMEM)

    def _help_test_inplace_minmaxmem(self, genstring, decomp, strlen):
        s = genstring(strlen)
        cs = zlibutil.zlib.compress(s)
        s2 = decomp(cs, maxlen=strlen, maxmem=zlibutil.MINMAXMEM)
        self.failUnless(s == s2)
        self.failUnlessRaises(zlibutil.TooBigError, decomp, cs, maxlen=strlen-1, maxmem=zlibutil.MINMAXMEM)

    def _help_test_inplace(self, genstring, decomp, strlen):
        # ### XXX self.failUnlessRaises(UnsafeDecompressError, decomp, zlib.compress(genstring(strlen)), maxlen=strlen, maxmem=strlen-1)
        s = genstring(strlen)
        cs = zlibutil.zlib.compress(s)
        s2 = decomp(cs, maxlen=strlen, maxmem=max(strlen*2**3, zlibutil.MINMAXMEM))
        self.failUnless(s == s2)
        s2 = decomp(cs, maxlen=strlen, maxmem=max(strlen*2**6, zlibutil.MINMAXMEM))
        self.failUnless(s == s2)
        s2 = decomp(cs, maxlen=strlen, maxmem=max(strlen-1, zlibutil.MINMAXMEM))
        self.failUnless(s == s2)
        s2 = decomp(cs, maxlen=strlen, maxmem=max(strlen/2, zlibutil.MINMAXMEM))
        self.failUnless(s == s2)
        self.failUnlessRaises(zlibutil.TooBigError, decomp, cs, maxlen=strlen-1, maxmem=max(strlen*2**3, zlibutil.MINMAXMEM))

    def testem(self):
        # for strlen in [2**1, 2**2, 2**10, 2**14, 2**21]: # a *real* test ought to include 2**21, which exercises different cases re: maxmem.  But it takes too long.
        for strlen in [2, 3, 4, 99,]:
            # print "strlen: %s\n" % (strlen,)
            for decomp in [zlibutil.decompress, make_decomp(zlibutil.decompress_to_fileobj), make_decomp(zlibutil.decompress_to_spool),]:
                # print "decomp: %s\n" % (decomp,)
                for genstring in [genrandstr, genbombstr,]:
                    # print "genstring: %s\n" % (genstring,)
                    self._help_test(genstring, decomp, strlen)

            for decomp in [make_decomp(zlibutil.decompress_to_spool),]:
                # print "decomp: %s\n" % (decomp,)
                for genstring in [genrandstr, genbombstr,]:
                    # print "genstring: %s\n" % (genstring,)
                    self._help_test_inplace(genstring, decomp, strlen)
                    self._help_test_inplace_minmaxmem(genstring, decomp, strlen)

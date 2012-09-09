#!/usr/bin/env python

#  Copyright (c) 2002-2009 Zooko "Zooko" Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

import random, sys, traceback, unittest

from pyutil.assertutil import _assert

from pyutil import dictutil

class EqButNotIs:
    def __init__(self, x):
        self.x = x
        self.hash = int(random.randrange(0, 2**31))
    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.x,)
    def __hash__(self):
        return self.hash
    def __le__(self, other):
        return self.x <= other
    def __lt__(self, other):
        return self.x < other
    def __ge__(self, other):
        return self.x >= other
    def __gt__(self, other):
        return self.x > other
    def __ne__(self, other):
        return self.x != other
    def __eq__(self, other):
        return self.x == other

class Testy(unittest.TestCase):
    def _help_test_empty_dict(self, klass):
        d1 = klass()
        d2 = klass({})

        self.failUnless(d1 == d2, "d1: %r, d2: %r" % (d1, d2,))
        self.failUnless(len(d1) == 0)
        self.failUnless(len(d2) == 0)

    def _help_test_nonempty_dict(self, klass):
        d1 = klass({'a': 1, 'b': "eggs", 3: "spam",})
        d2 = klass({'a': 1, 'b': "eggs", 3: "spam",})

        self.failUnless(d1 == d2)
        self.failUnless(len(d1) == 3, "%s, %s" % (len(d1), d1,))
        self.failUnless(len(d2) == 3)

    def _help_test_eq_but_notis(self, klass):
        d = klass({'a': 3, 'b': EqButNotIs(3), 'c': 3})
        d.pop('b')

        d.clear()
        d['a'] = 3
        d['b'] = EqButNotIs(3)
        d['c'] = 3
        d.pop('b')

        d.clear()
        d['b'] = EqButNotIs(3)
        d['a'] = 3
        d['c'] = 3
        d.pop('b')

        d.clear()
        d['a'] = EqButNotIs(3)
        d['c'] = 3
        d['a'] = 3

        d.clear()
        fake3 = EqButNotIs(3)
        fake7 = EqButNotIs(7)
        d[fake3] = fake7
        d[3] = 7
        d[3] = 8
        _assert(filter(lambda x: x is 8,  d.itervalues()))
        _assert(filter(lambda x: x is fake7,  d.itervalues()))
        _assert(not filter(lambda x: x is 7,  d.itervalues())) # The real 7 should have been ejected by the d[3] = 8.
        _assert(filter(lambda x: x is fake3,  d.iterkeys()))
        _assert(filter(lambda x: x is 3,  d.iterkeys()))
        d[fake3] = 8

        d.clear()
        d[3] = 7
        fake3 = EqButNotIs(3)
        fake7 = EqButNotIs(7)
        d[fake3] = fake7
        d[3] = 8
        _assert(filter(lambda x: x is 8,  d.itervalues()))
        _assert(filter(lambda x: x is fake7,  d.itervalues()))
        _assert(not filter(lambda x: x is 7,  d.itervalues())) # The real 7 should have been ejected by the d[3] = 8.
        _assert(filter(lambda x: x is fake3,  d.iterkeys()))
        _assert(filter(lambda x: x is 3,  d.iterkeys()))
        d[fake3] = 8

    def test_em(self):
        for klass in (dictutil.UtilDict, dictutil.NumDict, dictutil.ValueOrderedDict,):
            # print "name of class: ", klass
            for helper in (self._help_test_empty_dict, self._help_test_nonempty_dict, self._help_test_eq_but_notis,):
                # print "name of test func: ", helper
                try:
                    helper(klass)
                except:
                    (etype, evalue, realtb) = sys.exc_info()
                    traceback.print_exception(etype, evalue, realtb)
                    self.fail(evalue)
                    del realtb

def suite():
    suite = unittest.makeSuite(Testy, 'test')
    return suite

if __name__ == '__main__':
    unittest.main()

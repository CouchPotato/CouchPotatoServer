#!/usr/bin/env python

#  Copyright (c) 2002-2010 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

import random, unittest

from pyutil.humanreadable import hr
from pyutil import memutil
from pyutil import odict

class Bencher:
    def __init__(self, klass, MAXREPS=2**8, MAXTIME=5):
        print klass
        self.klass = klass
        self.MAXREPS = MAXREPS
        self.MAXTIME = MAXTIME
        self.d = {}
        self.lrun = None

    def _generic_benchmarking_init(self, n):
        self.d.clear()
        self.lrun = self.klass()
        for i in range(n):
            self.d[i] = i
            self.lrun[n+i] = n+i

    def _benchmark_init(self, n):
        d2 = self.klass(initialdata=self.d)
        assert len(d2) == len(self.d)
        return True

    def _benchmark_update(self, n):
        d2 = self.klass()
        assert len(d2) == 0
        d2.update(self.d)
        assert len(d2) == len(self.d)
        return True

    def _benchmark_insert(self, n):
        d2 = self.klass()
        assert len(d2) == 0
        for k, v, in self.d.iteritems():
            d2[k] = v
        assert len(d2) == len(self.d)
        return True

    def _benchmark_init_and_popitem(self, n):
        d2 = self.klass(initialdata=self.d)
        assert len(d2) == len(self.d)
        for i in range(len(d2), 0, -1):
            assert len(d2) == i
            d2.popitem()
        return True

    def _benchmark_init_and_has_key_and_del(self, n):
        d2 = self.klass(initialdata=self.d)
        assert len(d2) == len(self.d)
        for k in self.d.iterkeys():
            if d2.has_key(k):
                del d2[k]
        return True

    def _benchmark_init_and_remove(self, n):
        d2 = self.klass(initialdata=self.d)
        assert len(d2) == len(self.d)
        for k in self.d.iterkeys():
            d2.remove(k, strictkey=False)
        return True

    def bench(self, BSIZES=(128, 250, 2048, 5000, 2**13, 2**20,)):
        from pyutil import benchutil
        funcs = ("_benchmark_insert", "_benchmark_init_and_has_key_and_del", "_benchmark_init_and_remove", "_benchmark_init_and_popitem", "_benchmark_update", "_benchmark_init",)
        max = 0
        for func in funcs:
            if len(func) > max:
                max = len(func)
        for func in funcs:
            print func + " " * (max + 1 - len(func))
            for BSIZE in BSIZES:
                f = getattr(self, func)
                benchutil.rep_bench(f, BSIZE, self._generic_benchmarking_init, MAXREPS=self.MAXREPS, MAXTIME=self.MAXTIME)

def quick_bench():
    Bencher(odict.LRUCache, MAXTIME=2).bench(BSIZES=(2**7, 2**12, 2**14, 2**15, 2**16,))
    Bencher(odict.LinkedListLRUCache, MAXTIME=2).bench(BSIZES=(2**7, 2**12, 2**14, 2**15,))
    Bencher(odict.SmallLRUCache, MAXTIME=2).bench(BSIZES=(2**7, 2**12, 2**14, 2**15,))

def slow_bench():
    Bencher(odict.LRUCache, MAXTIME=5).bench(BSIZES=[2**x for x in range(7, 21)])
    Bencher(odict.LinkedListLRUCache, MAXTIME=5).bench(BSIZES=[2**x for x in range(7, 21)])
    Bencher(odict.SmallLRUCache, MAXTIME=5).bench(BSIZES=[2**x for x in range(7, 17)])

MUCHADDINGSIZE=2**4

# The following parameters are for testing for memory leakage.
MIN_SLOPE = 512.0 # If it leaks less than 512.0 bytes per iteration, then it's probably just some kind of noise from the interpreter or something...
SAMPLES = 2**5
# MIN_SLOPE is high because samples is low, which is because taking a statistically useful numbers of samples takes too long.
# For a *good* test, turn samples up as high as you can stand (maybe 2**10) and set MIN_SLOPE to about 1.0.
# For a *really* good test, add a variance measure to memutil.measure_mem_leakage(), and only consider it to be leaking if the slope is > 0.1 *and* is a "pretty good" fit for the data.
# MIN_SLOPE = 1.0
# SAMPLES = 2**10

class Testy(unittest.TestCase):
    def _test_empty_lookup(self, d) :
        self.failUnless(d.get('spam') is None)

    def _test_key_error(self, C) :
        d = C()
        try:
            d['spam']
            self.fail(d)
        except KeyError :
            pass

    def _test_insert_and_get_and_items(self, d) :
        d.insert("spam", "eggs")
        d["spam2"] = "eggs2"
        self.failUnless(d.get("spam") == "eggs", str(d))
        self.failUnless(d.get("spam2") == "eggs2")
        self.failUnless(d["spam"] == "eggs")
        self.failUnless(d["spam2"] == "eggs2")
        self.failUnlessEqual(d.items(), [("spam", "eggs"), ("spam2", "eggs2")], d)

    def _test_move_to_most_recent(self, d) :
        d.insert("spam", "eggs")
        d["spam2"] = "eggs2"
        self.failUnless(d.get("spam") == "eggs", str(d))
        self.failUnless(d.get("spam2") == "eggs2")
        self.failUnless(d["spam"] == "eggs")
        self.failUnless(d["spam2"] == "eggs2")
        self.failUnlessEqual(d.items(), [("spam", "eggs"), ("spam2", "eggs2")])
        d.move_to_most_recent("spam")
        self.failUnlessEqual(d.items(), [("spam2", "eggs2"), ("spam", "eggs")])

    def _test_insert_and_remove(self, d):
        d.insert('spam', "eggs")
        self.failUnless(d.has_key('spam'))
        self.failUnless(d.get('spam') == "eggs")
        self.failUnless(d['spam'] == "eggs")
        self.failUnlessEqual(d.items(), [("spam", "eggs")])
        x = d.remove('spam')
        self.failUnless(x == "eggs", "x: %s" % `x`)
        self.failUnless(not d.has_key('spam'))
        self.failUnlessEqual(d.items(), [])
        d['spam'] = "eggsy"
        self.failUnless(d.has_key('spam'))
        self.failUnless(d.get('spam') == "eggsy")
        self.failUnless(d['spam'] == "eggsy")
        self.failUnlessEqual(d.items(), [("spam", "eggsy")])
        del d['spam']
        self.failUnless(not d.has_key('spam'))
        self.failUnlessEqual(d.items(), [])

    def _test_setdefault(self, d):
        d.setdefault('spam', "eggs")
        self.failUnless(d.has_key('spam'))
        self.failUnless(d.get('spam') == "eggs")
        self.failUnless(d['spam'] == "eggs")
        self.failUnlessEqual(d.items(), [("spam", "eggs")])
        x = d.remove('spam')
        self.failUnless(x == "eggs", "x: %s" % `x`)
        self.failUnless(not d.has_key('spam'))
        self.failUnlessEqual(d.items(), [])

    def _test_extracted_bound_method(self, d):
        insmeth = d.insert
        insmeth('spammy', "eggsy")
        self.failUnless(d.get('spammy') == "eggsy")

    def _test_extracted_unbound_method(self, d):
        insumeth = d.__class__.insert
        insumeth(d, 'spammy', "eggsy")
        self.failUnless(d.get('spammy') == "eggsy")

    def _test_unbound_method(self, C, d):
        umeth = C.insert
        umeth(d, 'spammy', "eggsy")
        self.failUnless(d.get('spammy') == "eggsy")

    def _test_clear(self, d):
        d[11] = 11
        d._assert_invariants()
        self.failUnless(len(d) == 1)
        d.clear()
        d._assert_invariants()
        self.failUnless(len(d) == 0)
        self.failUnlessEqual(d.items(), [])

    def _test_update_from_dict(self, d):
        self.failUnless(d._assert_invariants())
        d['b'] = 99
        self.failUnless(d._assert_invariants())
        d2={ 'a': 0, 'b': 1, 'c': 2,}
        d.update(d2)
        self.failUnless(d._assert_invariants())
        self.failUnless(d.get('a') == 0, "d.get('a'): %s" % d.get('a'))
        self.failUnless(d._assert_invariants())
        self.failUnless(d.get('b') == 1, "d.get('b'): %s" % d.get('b'))
        self.failUnless(d._assert_invariants())
        self.failUnless(d.get('c') == 2)
        self.failUnless(d._assert_invariants())

    def _test_update_from_odict(self, d):
        self.failUnless(d._assert_invariants())
        d['b'] = 99
        self.failUnless(d._assert_invariants())
        d2 = odict.OrderedDict()
        d2['a'] = 0
        d2['b'] = 1
        d2['c'] = 2
        d.update(d2)
        self.failUnless(d._assert_invariants())
        self.failUnless(d.get('a') == 0, "d.get('a'): %s" % d.get('a'))
        self.failUnless(d._assert_invariants())
        self.failUnless(d.get('b') == 1, "d.get('b'): %s" % d.get('b'))
        self.failUnless(d._assert_invariants())
        self.failUnless(d.get('c') == 2)
        self.failUnless(d._assert_invariants())
        self.failUnlessEqual(d.items(), [("b", 1), ("a", 0), ("c", 2)])

    def _test_popitem(self, C):
        c = C({"a": 1})
        res = c.popitem()
        self.failUnlessEqual(res, ("a", 1,))

        c["a"] = 1
        c["b"] = 2

        res = c.popitem()
        self.failUnlessEqual(res, ("b", 2,))

    def _test_pop(self, C):
        c = C({"a": 1})
        res = c.pop()
        self.failUnlessEqual(res, "a")

        c["a"] = 1
        c["b"] = 2

        res = c.pop()
        self.failUnlessEqual(res, "b")

    def _test_iterate_items(self, C):
        c = C({"a": 1})
        c["b"] = 2
        i = c.iteritems()
        x = i.next()
        self.failUnlessEqual(x, ("a", 1,))
        x = i.next()
        self.failUnlessEqual(x, ("b", 2,))
        try:
            i.next()
            self.fail() # Should have gotten StopIteration exception
        except StopIteration:
            pass

    def _test_iterate_keys(self, C):
        c = C({"a": 1})
        c["b"] = 2
        i = c.iterkeys()
        x = i.next()
        self.failUnlessEqual(x, "a")
        x = i.next()
        self.failUnlessEqual(x, "b")
        try:
            i.next()
            self.fail() # Should have gotten StopIteration exception
        except StopIteration:
            pass

    def _test_iterate_values(self, C):
        c = C({"a": 1})
        c["b"] = 2
        i = c.itervalues()
        x = i.next()
        self.failUnless(x == 1)
        x = i.next()
        self.failUnless(x == 2)
        try:
            i.next()
            self.fail() # Should have gotten StopIteration exception
        except StopIteration:
            pass

    def _test_much_adding_some_removing(self, C):
        c = C()
        for i in range(MUCHADDINGSIZE):
            c[i] = i
            if (i % 4) == 0:
                k = random.choice(c.keys())
                del c[k]
        for i in range(MUCHADDINGSIZE):
            c[i] = i
        self.failUnlessEqual(len(c), MUCHADDINGSIZE)

    def _test_1(self, C):
        c = C()
        c[11] = 11
        c._assert_invariants()
        c[11] = 11
        c._assert_invariants()
        c[11] = 1001
        c._assert_invariants()
        c[11] = 11
        c._assert_invariants()
        c[11] = 1001
        c._assert_invariants()
        c[11] = 1001
        c._assert_invariants()
        c[11] = 1001
        c._assert_invariants()

    def _test_2(self, C):
        c = C()
        c[11] = 11
        c._assert_invariants()
        del c[11]
        c._assert_invariants()
        c[11] = 11
        c._assert_invariants()
        c[11] = 11
        c._assert_invariants()

    def _test_3(self, C):
        c = C()
        c[11] = 11
        c._assert_invariants()
        c[11] = 12
        c._assert_invariants()
        c[11] = 13
        c._assert_invariants()
        del c[11]
        c._assert_invariants()
        c[11] = 14
        c._assert_invariants()
        c[11] = 15
        c._assert_invariants()
        c[11] = 16
        c._assert_invariants()

    def _test_has_key(self, C):
        c = C()
        c._assert_invariants()
        for i in xrange(11):
            c._assert_invariants()
            c[i] = i
            c._assert_invariants()
        del c[0]
        self.failUnless(len(c) == 10)
        self.failUnless(10 in c.values())
        self.failUnless(0 not in c.values())

        c.has_key(1) # this touches `1' but does not make it fresher so that it will get popped next time we pop.
        c[1] = 1 # this touches `1' but does not make it fresher so that it will get popped.
        c._assert_invariants()

        x = c.pop()
        self.failUnlessEqual(x, 10)

        c[99] = 99
        c._assert_invariants()
        self.failUnless(len(c) == 10)
        self.failUnless(1 in c.values(), "C: %s, c.values(): %s" % (hr(C), hr(c.values(),),))
        self.failUnless(2 in c.values(), "C: %s, c.values(): %s" % (hr(C), hr(c.values(),),))
        self.failIf(10 in c.values(), "C: %s, c.values(): %s" % (hr(C), hr(c.values(),),))
        self.failUnless(99 in c.values())

    def _test_em(self):
        for klass in (odict.OrderedDict,):
            for testfunc in (self._test_empty_lookup, self._test_insert_and_get_and_items, self._test_insert_and_remove, self._test_extracted_bound_method, self._test_extracted_unbound_method, self._test_clear, self._test_update_from_dict, self._test_update_from_odict, self._test_setdefault,):
                testfunc(klass())

            for testfunc in (self._test_pop, self._test_popitem, self._test_iterate_items, self._test_iterate_keys, self._test_iterate_values, self._test_key_error, ):
                testfunc(klass)

            self._test_unbound_method(klass, klass())

        for klass in (odict.OrderedDict,):
            for testfunc in (self._test_1, self._test_2, self._test_3, self._test_has_key,):
                testfunc(klass)

    def test_em(self):
        self._test_em()

    def _mem_test_much_adding_some_removing(self):
        for klass in (odict.LRUCache, odict.SmallLRUCache,):
            return self._test_much_adding_some_removing(klass)

    def test_mem_leakage(self):
        try:
            self._test_mem_leakage()
        except memutil.NotSupportedException:
            print "Skipping memory leak test since measurement of current mem usage isn't implemented on this platform."
            pass
    del test_mem_leakage # This test takes too long.

    def _test_mem_leakage(self):
        # measure one and throw it away, in order to reach a "steady state" in terms of initialization of memory state.
        memutil.measure_mem_leakage(self.test_em, max(2**3, SAMPLES/2**3), iterspersample=2**0)
        slope = memutil.measure_mem_leakage(self.test_em, max(2**3, SAMPLES/2**3), iterspersample=2**0)

        self.failUnless(slope <= MIN_SLOPE, "%s leaks memory at a rate of approximately %s system bytes per invocation" % (self.test_em, "%0.3f" % slope,))

    def test_mem_leakage_much_adding_some_removing(self):
        try:
            self._test_mem_leakage_much_adding_some_removing()
        except memutil.NotSupportedException:
            print "Skipping memory leak test since measurement of current mem usage isn't implemented on this platform."
            pass
    del test_mem_leakage_much_adding_some_removing # This test takes too long.

    def _test_mem_leakage_much_adding_some_removing(self):
        # measure one and throw it away, in order to reach a "steady state" in terms of initialization of memory state.
        memutil.measure_mem_leakage(self._mem_test_much_adding_some_removing, SAMPLES, iterspersample=2**0)
        slope = memutil.measure_mem_leakage(self._mem_test_much_adding_some_removing, SAMPLES, iterspersample=2**0)

        self.failUnless(slope <= MIN_SLOPE, "%s leaks memory at a rate of approximately %s system bytes per invocation" % (self._mem_test_much_adding_some_removing, "%0.3f" % slope,))

    def test_obj_leakage(self):
        self._test_obj_leakage()
    del test_obj_leakage # This test takes too long.

    def _test_obj_leakage(self):
        # measure one and throw it away, in order to reach a "steady state" in terms of initialization of objects state.
        memutil.measure_obj_leakage(self.test_em, max(2**3, SAMPLES/2**3), iterspersample=2**0)
        slope = memutil.measure_obj_leakage(self.test_em, max(2**3, SAMPLES/2**3), iterspersample=2**0)

        self.failUnless(slope <= MIN_SLOPE, "%s leaks objects at a rate of approximately %s system bytes per invocation" % (self.test_em, "%0.3f" % slope,))

    def test_obj_leakage_much_adding_some_removing(self):
        self._test_obj_leakage_much_adding_some_removing()
    del test_obj_leakage_much_adding_some_removing # This test takes too long.

    def _test_obj_leakage_much_adding_some_removing(self):
        # measure one and throw it away, in order to reach a "steady state" in terms of initialization of objects state.
        memutil.measure_obj_leakage(self._mem_test_much_adding_some_removing, SAMPLES, iterspersample=2**0)
        slope = memutil.measure_obj_leakage(self._mem_test_much_adding_some_removing, SAMPLES, iterspersample=2**0)

        self.failUnless(slope <= MIN_SLOPE, "%s leaks objects at a rate of approximately %s system bytes per invocation" % (self._mem_test_much_adding_some_removing, "%0.3f" % slope,))

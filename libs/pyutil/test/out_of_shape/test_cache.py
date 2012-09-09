#!/usr/bin/env python

#  Copyright (c) 2002-2010 Zooko "Zooko" Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

import random, unittest

from pyutil.assertutil import _assert

from pyutil.humanreadable import hr
from pyutil import memutil
from pyutil import cache

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
        global lrun
        self.lrun = self.klass(maxsize=n)
        for i in range(n):
            self.d[i] = i
            self.lrun[n+i] = n+i

    def _benchmark_init(self, n):
        MAXSIZE=n/2
        d2 = self.klass(initialdata=self.d, maxsize=MAXSIZE)
        assert len(d2) == min(len(self.d), MAXSIZE)
        return True

    def _benchmark_update(self, n):
        MAXSIZE=n/2
        d2 = self.klass(maxsize=MAXSIZE)
        assert len(d2) == 0
        d2.update(self.d)
        assert len(d2) == min(len(self.d), MAXSIZE)
        return True

    def _benchmark_insert(self, n):
        MAXSIZE=n/2
        d2 = self.klass(maxsize=MAXSIZE)
        assert len(d2) == 0
        for k, v, in self.d.iteritems():
            d2[k] = v
        assert len(d2) == min(len(self.d), MAXSIZE)
        return True

    def _benchmark_init_and_popitem(self, n):
        MAXSIZE=n/2
        d2 = self.klass(initialdata=self.d, maxsize=MAXSIZE)
        assert len(d2) == min(len(self.d), MAXSIZE)
        for i in range(len(d2), 0, -1):
            assert len(d2) == i
            d2.popitem()
        return True

    def _benchmark_init_and_has_key_and_del(self, n):
        MAXSIZE=n/2
        d2 = self.klass(initialdata=self.d, maxsize=MAXSIZE)
        assert len(d2) == min(len(self.d), MAXSIZE)
        for k in self.d.iterkeys():
            if d2.has_key(k):
                del d2[k]
        return True

    def _benchmark_init_and_remove(self, n):
        MAXSIZE=n/2
        d2 = self.klass(initialdata=self.d, maxsize=MAXSIZE)
        assert len(d2) == min(len(self.d), MAXSIZE)
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
    Bencher(cache.LRUCache, MAXTIME=2).bench(BSIZES=(2**7, 2**12, 2**14, 2**15, 2**16,))
    Bencher(cache.LinkedListLRUCache, MAXTIME=2).bench(BSIZES=(2**7, 2**12, 2**14, 2**15,))
    Bencher(cache.SmallLRUCache, MAXTIME=2).bench(BSIZES=(2**7, 2**12, 2**14, 2**15,))

def slow_bench():
    Bencher(cache.LRUCache, MAXTIME=5).bench(BSIZES=[2**x for x in range(7, 21)])
    Bencher(cache.LinkedListLRUCache, MAXTIME=5).bench(BSIZES=[2**x for x in range(7, 21)])
    Bencher(cache.SmallLRUCache, MAXTIME=5).bench(BSIZES=[2**x for x in range(7, 17)])

MUCHADDINGSIZE=2**4
MUCHADDINGNUM = 2**4

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

    def _test_insert_and_get(self, d) :
        d.insert("spam", "eggs")
        d["spam2"] = "eggs2"
        self.failUnless(d.get("spam") == "eggs", str(d))
        self.failUnless(d.get("spam2") == "eggs2")
        self.failUnless(d["spam"] == "eggs")
        self.failUnless(d["spam2"] == "eggs2")

    def _test_insert_and_remove(self, d):
        d.insert('spam', "eggs")
        self.failUnless(d.has_key('spam'))
        self.failUnless(d.get('spam') == "eggs")
        self.failUnless(d['spam'] == "eggs")
        x = d.remove('spam')
        self.failUnless(x == "eggs", "x: %s" % `x`)
        self.failUnless(not d.has_key('spam'))
        d['spam'] = "eggs"
        self.failUnless(d.has_key('spam'))
        self.failUnless(d.get('spam') == "eggs")
        self.failUnless(d['spam'] == "eggs")
        del d['spam']
        self.failUnless(not d.has_key('spam'))

    def _test_setdefault(self, d):
        d.setdefault('spam', "eggs")
        self.failUnless(d.has_key('spam'))
        self.failUnless(d.get('spam') == "eggs")
        self.failUnless(d['spam'] == "eggs")
        x = d.remove('spam')
        self.failUnless(x == "eggs", "x: %s" % `x`)
        self.failUnless(not d.has_key('spam'))

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

    def _test_update(self, d):
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

    def _test_popitem(self, C):
        c = C({"a": 1})
        res = c.popitem()
        _assert(res == ("a", 1,), C, c, res)
        self.failUnless(res == ("a", 1,))

    def _test_iterate_items(self, C):
        c = C({"a": 1})
        i = c.iteritems()
        x = i.next()
        self.failUnless(x == ("a", 1,))
        try:
            i.next()
            self.fail() # Should have gotten StopIteration exception
        except StopIteration:
            pass

    def _test_iterate_keys(self, C):
        c = C({"a": 1})
        i = c.iterkeys()
        x = i.next()
        self.failUnless(x == "a")
        try:
            i.next()
            self.fail() # Should have gotten StopIteration exception
        except StopIteration:
            pass

    def _test_iterate_values(self, C):
        c = C({"a": 1})
        i = c.itervalues()
        x = i.next()
        self.failUnless(x == 1)
        try:
            i.next()
            self.fail() # Should have gotten StopIteration exception
        except StopIteration:
            pass

    def _test_LRU_much_adding_some_removing(self, C):
        c = C(maxsize=MUCHADDINGSIZE)
        for i in range(MUCHADDINGNUM):
            c[i] = i
            if (i % 400) == 0:
                k = random.choice(c.keys())
                del c[k]
        for i in range(MUCHADDINGSIZE):
            c[i] = i
        self.failUnless(len(c) == MUCHADDINGSIZE)

    def _test_LRU_1(self, C):
        c = C(maxsize=10)
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

    def _test_LRU_2(self, C):
        c = C(maxsize=10)
        c[11] = 11
        c._assert_invariants()
        del c[11]
        c._assert_invariants()
        c[11] = 11
        c._assert_invariants()
        c[11] = 11
        c._assert_invariants()

    def _test_LRU_3(self, C):
        c = C(maxsize=10)
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

    def _test_LRU_full(self, C):
        c = C(maxsize=10)
        c._assert_invariants()
        for i in xrange(11):
            c._assert_invariants()
            c[i] = i
            c._assert_invariants()
        self.failUnless(len(c) == 10)
        self.failUnless(10 in c.values(), c.values())
        self.failUnless(0 not in c.values())

        del c[1]
        c._assert_invariants()
        self.failUnless(1 not in c.values())
        self.failUnless(len(c) == 9)
        c[11] = 11
        c._assert_invariants()
        self.failUnless(len(c) == 10)
        self.failUnless(1 not in c.values())
        self.failUnless(11 in c.values())
        del c[11]
        c._assert_invariants()

        c[11] = 11
        c._assert_invariants()
        self.failUnless(len(c) == 10)
        self.failUnless(1 not in c.values())
        self.failUnless(11 in c.values())

        c[11] = 11
        c._assert_invariants()
        self.failUnless(len(c) == 10)
        self.failUnless(1 not in c.values())
        self.failUnless(11 in c.values())

        for i in xrange(200):
            c[i] = i
            c._assert_invariants()
        self.failUnless(199 in c.values())
        self.failUnless(190 in c.values())

    def _test_LRU_has_key(self, C):
        c = C(maxsize=10)
        c._assert_invariants()
        for i in xrange(11):
            c._assert_invariants()
            c[i] = i
            c._assert_invariants()
        self.failUnless(len(c) == 10)
        self.failUnless(10 in c.values())
        self.failUnless(0 not in c.values())

        # c.has_key(1) # this touches `1' and makes it fresher so that it will live and `2' will die next time we overfill.
        c[1] = 1 # this touches `1' and makes it fresher so that it will live and `2' will die next time we overfill.
        c._assert_invariants()

        c[99] = 99
        c._assert_invariants()
        self.failUnless(len(c) == 10)
        self.failUnless(1 in c.values(), "C: %s, c.values(): %s" % (hr(C), hr(c.values(),),))
        self.failUnless(not 2 in c.values())
        self.failUnless(99 in c.values())

    def _test_LRU_not_overfull_on_idempotent_add(self, C):
        c = C(maxsize=10)
        for i in xrange(11):
            c[i] = i
        c[1] = "spam"
        # Now 1 is the freshest, so 2 is the next one that would be removed *if* we went over limit.
        c[3] = "eggs"
        self.failUnless(c.has_key(2))
        self.failUnless(len(c) == 10)
        c._assert_invariants()

    def _test_LRU_overflow_on_update(self, C):
        d = C(maxsize=10)
        self.failUnless(d._assert_invariants())
        d2 = {}
        for i in range(12):
            d2[i] = i
        d.update(d2)
        self.failUnless(d._assert_invariants())
        self.failUnless(len(d) == 10)

    def _test_LRU_overflow_on_init(self, C):
        d2 = {}
        for i in range(12):
            d2[i] = i
        d = C(d2, maxsize=10)
        self.failUnless(d._assert_invariants())
        self.failUnless(len(d) == 10)

    def _test_em(self):
        for klass in (cache.LRUCache, cache.SmallLRUCache,):
            for testfunc in (self._test_empty_lookup, self._test_insert_and_get, self._test_insert_and_remove, self._test_extracted_bound_method, self._test_extracted_unbound_method, self._test_clear, self._test_update, self._test_setdefault,):
                testfunc(klass())

            for testfunc in (self._test_popitem, self._test_iterate_items, self._test_iterate_keys, self._test_iterate_values, self._test_key_error, ):
                testfunc(klass)

            self._test_unbound_method(klass, klass())

        for klass in (cache.LRUCache, cache.SmallLRUCache,):
            for testfunc in (self._test_LRU_1, self._test_LRU_2, self._test_LRU_3, self._test_LRU_full, self._test_LRU_has_key, self._test_LRU_not_overfull_on_idempotent_add, self._test_LRU_overflow_on_update, self._test_LRU_overflow_on_init,):
                testfunc(klass)

    def test_em(self):
        self._test_em()

    def _mem_test_LRU_much_adding_some_removing(self):
        for klass in (cache.LRUCache, cache.SmallLRUCache,):
            return self._test_LRU_much_adding_some_removing(klass)

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
        memutil.measure_mem_leakage(self._mem_test_LRU_much_adding_some_removing, SAMPLES, iterspersample=2**0)
        slope = memutil.measure_mem_leakage(self._mem_test_LRU_much_adding_some_removing, SAMPLES, iterspersample=2**0)

        self.failUnless(slope <= MIN_SLOPE, "%s leaks memory at a rate of approximately %s system bytes per invocation" % (self._mem_test_LRU_much_adding_some_removing, "%0.3f" % slope,))

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
        memutil.measure_obj_leakage(self._mem_test_LRU_much_adding_some_removing, SAMPLES, iterspersample=2**0)
        slope = memutil.measure_obj_leakage(self._mem_test_LRU_much_adding_some_removing, SAMPLES, iterspersample=2**0)

        self.failUnless(slope <= MIN_SLOPE, "%s leaks objects at a rate of approximately %s system bytes per invocation" % (self._mem_test_LRU_much_adding_some_removing, "%0.3f" % slope,))

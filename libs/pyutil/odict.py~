#  Copyright (c) 2002-2009 Zooko "Zooko" Wilcox-O'Hearn

"""
This module offers a Ordered Dict, which is a dict that preserves
insertion order.  See PEP 372 for description of the problem.  This
implementation uses a linked-list to get good O(1) asymptotic
performance.  (Actually it is O(hashtable-update-cost), but whatever.)

Warning: if -O optimizations are not turned on then OrderedDict performs
extensive self-analysis in every function call, which can take minutes
and minutes for a large cache.  Turn on -O, or comment out assert
self._assert_invariants()
"""

import operator

from assertutil import _assert, precondition
from humanreadable import hr

class OrderedDict:
    """
    An efficient ordered dict.

    Adding an item that is already in the dict *does not* make it the
    most- recently-added item although it may change the state of the
    dict itself (if the value is different than the previous value).

    See also SmallOrderedDict (below), which is faster in some cases.
    """
    class ItemIterator:
        def __init__(self, c):
            self.c = c
            self.i = c.d[c.ts][1]
        def __iter__(self):
            return self
        def next(self):
            if self.i is self.c.hs:
                raise StopIteration
            k = self.i
            precondition(self.c.d.has_key(k), "The iterated OrderedDict doesn't have the next key.  Most likely this is because someone altered the contents of the OrderedDict while the iteration was in progress.", k, self.c)
            (v, p, n,) = self.c.d[k]
            self.i = p
            return (k, v,)

    class KeyIterator:
        def __init__(self, c):
            self.c = c
            self.i = c.d[c.ts][1]
        def __iter__(self):
            return self
        def next(self):
            if self.i is self.c.hs:
                raise StopIteration
            k = self.i
            precondition(self.c.d.has_key(k), "The iterated OrderedDict doesn't have the next key.  Most likely this is because someone altered the contents of the OrderedDict while the iteration was in progress.", k, self.c)
            (v, p, n,) = self.c.d[k]
            self.i = p
            return k

    class ValIterator:
        def __init__(self, c):
            self.c = c
            self.i = c.d[c.ts][1]
        def __iter__(self):
            return self
        def next(self):
            if self.i is self.c.hs:
                raise StopIteration
            precondition(self.c.d.has_key(self.i), "The iterated OrderedDict doesn't have the next key.  Most likely this is because someone altered the contents of the OrderedDict while the iteration was in progress.", self.i, self.c)
            (v, p, n,) = self.c.d[self.i]
            self.i = p
            return v

    class Sentinel:
        def __init__(self, msg):
            self.msg = msg
        def __repr__(self):
            return "<%s %s>" % (self.__class__.__name__, self.msg,)

    def __init__(self, initialdata={}):
        self.d = {} # k: k, v: [v, prev, next,] # the dict
        self.hs = OrderedDict.Sentinel("hs")
        self.ts = OrderedDict.Sentinel("ts")
        self.d[self.hs] = [None, self.hs, self.ts,] # This allows us to use sentinels as normal nodes.
        self.d[self.ts] = [None, self.hs, self.ts,] # This allows us to use sentinels as normal nodes.
        self.update(initialdata)

        assert self._assert_invariants()

    def __repr_n__(self, n=None):
        s = ["{",]
        try:
            iter = self.iteritems()
            x = iter.next()
            s.append(str(x[0])); s.append(": "); s.append(str(x[1]))
            i = 1
            while (n is None) or (i < n):
                x = iter.next()
                s.append(", "); s.append(str(x[0])); s.append(": "); s.append(str(x[1]))
        except StopIteration:
            pass
        s.append("}")
        return ''.join(s)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.__repr_n__(),)

    def __str__(self):
        return "<%s %s>" % (self.__class__.__name__, self.__repr_n__(16),)

    def _assert_invariants(self):
        _assert((len(self.d) > 2) == (self.d[self.hs][2] is not self.ts) == (self.d[self.ts][1] is not self.hs), "Head and tail point to something other than each other if and only if there is at least one element in the dictionary.", self.hs, self.ts, len(self.d))
        foundprevsentinel = 0
        foundnextsentinel = 0
        for (k, (v, p, n,)) in self.d.iteritems():
            _assert(v not in (self.hs, self.ts,))
            _assert(p is not self.ts, "A reference to the tail sentinel may not appear in prev.", k, v, p, n)
            _assert(n is not self.hs, "A reference to the head sentinel may not appear in next.", k, v, p, n)
            _assert(p in self.d, "Each prev is required to appear as a key in the dict.", k, v, p, n)
            _assert(n in self.d, "Each next is required to appear as a key in the dict.", k, v, p, n)
            if p is self.hs:
                foundprevsentinel += 1
                _assert(foundprevsentinel <= 2, "No more than two references to the head sentinel may appear as a prev.", k, v, p, n)
            if n is self.ts:
                foundnextsentinel += 1
                _assert(foundnextsentinel <= 2, "No more than one reference to the tail sentinel may appear as a next.", k, v, p, n)
        _assert(foundprevsentinel == 2, "A reference to the head sentinel is required appear as a prev (plus a self-referential reference).")
        _assert(foundnextsentinel == 2, "A reference to the tail sentinel is required appear as a next (plus a self-referential reference).")

        count = 0
        for (k, v,) in self.iteritems():
            _assert(k not in (self.hs, self.ts,), k, self.hs, self.ts)
            count += 1
        _assert(count == len(self.d)-2, count, len(self.d)) # -2 for the sentinels

        return True

    def move_to_most_recent(self, k, strictkey=False):
        assert self._assert_invariants()

        if not self.d.has_key(k):
            if strictkey:
                raise KeyError, k
            return

        node = self.d[k]

        # relink
        self.d[node[1]][2] = node[2]
        self.d[node[2]][1] = node[1]

        # move to front
        hnode = self.d[self.hs]

        node[1] = self.hs
        node[2] = hnode[2]
        hnode[2] = k
        self.d[node[2]][1] = k

        assert self._assert_invariants()

    def iteritems(self):
        return OrderedDict.ItemIterator(self)

    def itervalues(self):
        return OrderedDict.ValIterator(self)

    def iterkeys(self):
        return self.__iter__()

    def __iter__(self):
        return OrderedDict.KeyIterator(self)

    def __getitem__(self, key, default=None, strictkey=True):
        node = self.d.get(key)
        if not node:
            if strictkey:
                raise KeyError, key
            return default
        return node[0]

    def __setitem__(self, k, v=None):
        assert self._assert_invariants()

        node = self.d.get(k)
        if node:
            node[0] = v
            return

        hnode = self.d[self.hs]
        n = hnode[2]
        self.d[k] = [v, self.hs, n,]
        hnode[2] = k
        self.d[n][1] = k

        assert self._assert_invariants()
        return v

    def __delitem__(self, key, default=None, strictkey=True):
        """
        @param strictkey: True if you want a KeyError in the case that
            key is not there, False if you want a reference to default
            in the case that key is not there
        @param default: the object to return if key is not there; This
            is ignored if strictkey.

        @return: the value removed or default if there is not item by
            that key and strictkey is False
        """
        assert self._assert_invariants()
        if self.d.has_key(key):
            node = self.d[key]
            # relink
            self.d[node[1]][2] = node[2]
            self.d[node[2]][1] = node[1]
            del self.d[key]
            assert self._assert_invariants()
            return node[0]
        elif strictkey:
            assert self._assert_invariants()
            raise KeyError, key
        else:
            assert self._assert_invariants()
            return default

    def has_key(self, key):
        assert self._assert_invariants()
        if self.d.has_key(key):
            assert self._assert_invariants()
            return True
        else:
            assert self._assert_invariants()
            return False

    def clear(self):
        assert self._assert_invariants()
        self.d.clear()
        self.d[self.hs] = [None, self.hs, self.ts,] # This allows us to use sentinels as normal nodes.
        self.d[self.ts] = [None, self.hs, self.ts,] # This allows us to use sentinels as normal nodes.
        assert self._assert_invariants()

    def update(self, otherdict):
        """
        @return: self
        """
        assert self._assert_invariants()

        for (k, v,) in otherdict.iteritems():
            assert self._assert_invariants()
            self[k] = v
            assert self._assert_invariants()

    def pop(self):
        assert self._assert_invariants()
        if len(self.d) < 2: # the +2 is for the sentinels
            raise KeyError, 'popitem(): dictionary is empty'
        k = self.d[self.hs][2]
        self.remove(k)
        assert self._assert_invariants()
        return k

    def popitem(self):
        assert self._assert_invariants()
        if len(self.d) < 2: # the +2 is for the sentinels
            raise KeyError, 'popitem(): dictionary is empty'
        k = self.d[self.hs][2]
        val = self.remove(k)
        assert self._assert_invariants()
        return (k, val,)

    def keys_unsorted(self):
        assert self._assert_invariants()
        t = self.d.copy()
        del t[self.hs]
        del t[self.ts]
        assert self._assert_invariants()
        return t.keys()

    def keys(self):
        res = [None] * len(self)
        i = 0
        for k in self.iterkeys():
            res[i] = k
            i += 1
        return res

    def values_unsorted(self):
        assert self._assert_invariants()
        t = self.d.copy()
        del t[self.hs]
        del t[self.ts]
        assert self._assert_invariants()
        return map(operator.__getitem__, t.values(), [0]*len(t))

    def values(self):
        res = [None] * len(self)
        i = 0
        for v in self.itervalues():
            res[i] = v
            i += 1
        return res

    def items(self):
        res = [None] * len(self)
        i = 0
        for it in self.iteritems():
            res[i] = it
            i += 1
        return res

    def __len__(self):
        return len(self.d) - 2

    def insert(self, key, val=None):
        assert self._assert_invariants()
        result = self.__setitem__(key, val)
        assert self._assert_invariants()
        return result

    def setdefault(self, key, default=None):
        assert self._assert_invariants()
        if not self.has_key(key):
            self[key] = default
        assert self._assert_invariants()
        return self[key]

    def get(self, key, default=None):
        return self.__getitem__(key, default, strictkey=False)

    def remove(self, key, default=None, strictkey=True):
        assert self._assert_invariants()
        result = self.__delitem__(key, default, strictkey)
        assert self._assert_invariants()
        return result

class SmallOrderedDict(dict):
    """
    SmallOrderedDict is faster than OrderedDict for small sets.  How small?  That
    depends on your machine and which operations you use most often.  Use
    performance profiling to determine whether the cache class that you are
    using makes any difference to the performance of your program, and if it
    does, then run "quick_bench()" in test/test_cache.py to see which cache
    implementation is faster for the size of your datasets.

    A simple least-recently-used cache.  It keeps an LRU queue, and
    when the number of items in the cache reaches maxsize, it removes
    the least recently used item.

    "Looking" at an item or a key such as with "has_key()" makes that
    item become the most recently used item.

    You can also use "refresh()" to explicitly make an item become the most
    recently used item.

    Adding an item that is already in the dict *does* make it the
    most- recently-used item although it does not change the state of
    the dict itself.
    """
    class ItemIterator:
        def __init__(self, c):
            self.c = c
            self.i = 0
        def __iter__(self):
            return self
        def next(self):
            precondition(self.i <= len(self.c._lru), "The iterated SmallOrderedDict doesn't have this many elements.  Most likely this is because someone altered the contents of the OrderedDict while the iteration was in progress.", self.i, self.c)
            precondition(dict.has_key(self.c, self.c._lru[self.i]), "The iterated SmallOrderedDict doesn't have this key.  Most likely this is because someone altered the contents of the OrderedDict while the iteration was in progress.", self.i, self.c._lru[self.i], self.c)
            if self.i == len(self.c._lru):
                raise StopIteration
            k = self.i
            self.i += 1
            return (k, dict.__getitem__(self.c, k),)

    class KeyIterator:
        def __init__(self, c):
            self.c = c
            self.i = 0
        def __iter__(self):
            return self
        def next(self):
            precondition(self.i <= len(self.c._lru), "The iterated SmallOrderedDict doesn't have this many elements.  Most likely this is because someone altered the contents of the OrderedDict while the iteration was in progress.", self.i, self.c)
            precondition(dict.has_key(self.c, self.c._lru[self.i]), "The iterated SmallOrderedDict doesn't have this key.  Most likely this is because someone altered the contents of the OrderedDict while the iteration was in progress.", self.i, self.c._lru[self.i], self.c)
            if self.i == len(self.c._lru):
                raise StopIteration
            k = self.i
            self.i += 1
            return k

    class ValueIterator:
        def __init__(self, c):
            self.c = c
            self.i = 0
        def __iter__(self):
            return self
        def next(self):
            precondition(self.i <= len(self.c._lru), "The iterated SmallOrderedDict doesn't have this many elements.  Most likely this is because someone altered the contents of the OrderedDict while the iteration was in progress.", self.i, self.c)
            precondition(dict.has_key(self.c, self.c._lru[self.i]), "The iterated SmallOrderedDict doesn't have this key.  Most likely this is because someone altered the contents of the OrderedDict while the iteration was in progress.", self.i, self.c._lru[self.i], self.c)
            if self.i == len(self.c._lru):
                raise StopIteration
            k = self.i
            self.i += 1
            return dict.__getitem__(self.c, k)

    def __init__(self, initialdata={}, maxsize=128):
        dict.__init__(self, initialdata)
        self._lru = initialdata.keys() # contains keys
        self._maxsize = maxsize
        over = len(self) - self._maxsize
        if over > 0:
            map(dict.__delitem__, [self]*over, self._lru[:over])
            del self._lru[:over]
        assert self._assert_invariants()

    def _assert_invariants(self):
        _assert(len(self._lru) <= self._maxsize, "Size is required to be <= maxsize.")
        _assert(len(filter(lambda x: dict.has_key(self, x), self._lru)) == len(self._lru), "Each key in self._lru is required to be in dict.", filter(lambda x: not dict.has_key(self, x), self._lru), len(self._lru), self._lru, len(self), self)
        _assert(len(filter(lambda x: x in self._lru, self.keys())) == len(self), "Each key in dict is required to be in self._lru.", filter(lambda x: x not in self._lru, self.keys()), len(self._lru), self._lru, len(self), self)
        _assert(len(self._lru) == len(self), "internal consistency", filter(lambda x: x not in self.keys(), self._lru), len(self._lru), self._lru, len(self), self)
        _assert(len(self._lru) <= self._maxsize, "internal consistency", len(self._lru), self._lru, self._maxsize)
        return True

    def insert(self, key, item=None):
        assert self._assert_invariants()
        result = self.__setitem__(key, item)
        assert self._assert_invariants()
        return result

    def setdefault(self, key, default=None):
        assert self._assert_invariants()
        if not self.has_key(key):
            self[key] = default
        assert self._assert_invariants()
        return self[key]

    def __setitem__(self, key, item=None):
        assert self._assert_invariants()
        if dict.has_key(self, key):
            self._lru.remove(key)
        else:
            if len(self._lru) == self._maxsize:
                # If this insert is going to increase the size of the cache to bigger than maxsize:
                killkey = self._lru.pop(0)
                dict.__delitem__(self, killkey)
        dict.__setitem__(self, key, item)
        self._lru.append(key)
        assert self._assert_invariants()
        return item

    def remove(self, key, default=None, strictkey=True):
        assert self._assert_invariants()
        result = self.__delitem__(key, default, strictkey)
        assert self._assert_invariants()
        return result

    def __delitem__(self, key, default=None, strictkey=True):
        """
        @param strictkey: True if you want a KeyError in the case that
            key is not there, False if you want a reference to default
            in the case that key is not there
        @param default: the object to return if key is not there; This
            is ignored if strictkey.

        @return: the object removed or default if there is not item by
            that key and strictkey is False
        """
        assert self._assert_invariants()
        if dict.has_key(self, key):
            val = dict.__getitem__(self, key)
            dict.__delitem__(self, key)
            self._lru.remove(key)
            assert self._assert_invariants()
            return val
        elif strictkey:
            assert self._assert_invariants()
            raise KeyError, key
        else:
            assert self._assert_invariants()
            return default

    def clear(self):
        assert self._assert_invariants()
        dict.clear(self)
        self._lru = []
        assert self._assert_invariants()

    def update(self, otherdict):
        """
        @return: self
        """
        assert self._assert_invariants()
        if len(otherdict) > self._maxsize:
            # Handling this special case here makes it possible to implement the
            # other more common cases faster below.
            dict.clear(self)
            self._lru = []
            if self._maxsize > (len(otherdict) - self._maxsize):
                dict.update(self, otherdict)
                while len(self) > self._maxsize:
                    dict.popitem(self)
            else:
                for k, v, in otherdict.iteritems():
                    if len(self) == self._maxsize:
                        break
                    dict.__setitem__(self, k, v)
            self._lru = dict.keys(self)
            assert self._assert_invariants()
            return self
      
        for k in otherdict.iterkeys():
            if dict.has_key(self, k):
                self._lru.remove(k)
        self._lru.extend(otherdict.keys())
        dict.update(self, otherdict)

        over = len(self) - self._maxsize
        if over > 0:
            map(dict.__delitem__, [self]*over, self._lru[:over])
            del self._lru[:over]

        assert self._assert_invariants()
        return self

    def has_key(self, key):
        assert self._assert_invariants()
        if dict.has_key(self, key):
            assert key in self._lru, "key: %s, self._lru: %s" % tuple(map(hr, (key, self._lru,)))
            self._lru.remove(key)
            self._lru.append(key)
            assert self._assert_invariants()
            return True
        else:
            assert self._assert_invariants()
            return False

    def refresh(self, key, strictkey=True):
        """
        @param strictkey: raise a KeyError exception if key isn't present
        """
        assert self._assert_invariants()
        if not dict.has_key(self, key):
            if strictkey:
                raise KeyError, key
            return
        self._lru.remove(key)
        self._lru.append(key)

    def popitem(self):
        if not self._lru:
            raise KeyError, 'popitem(): dictionary is empty'
        k = self._lru[-1]
        obj = self.remove(k)
        return (k, obj,)

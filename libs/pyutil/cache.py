#  Copyright (c) 2002-2010 Zooko "Zooko" Wilcox-O'Hearn

"""
This module offers three implementations of an LRUCache, which is a dict that
drops items according to a Least-Recently-Used policy if the dict exceeds a
fixed maximum size.

Warning: if -O optimizations are not turned on then LRUCache performs
extensive self-analysis in every function call, which can take minutes
and minutes for a large cache.  Turn on -O, or comment out ``assert self._assert_invariants()``
"""

import operator

from assertutil import _assert, precondition
from humanreadable import hr

class LRUCache:
    """
    An efficient least-recently-used cache.  It keeps an LRU queue, and when
    the number of items in the cache reaches maxsize, it removes the least
    recently used item.

    "Looking" at an item, key, or value such as with "has_key()" makes that
    item become the most recently used item.

    You can also use "refresh()" to explicitly make an item become the most
    recently used item.

    Adding an item that is already in the dict *does* make it the most-
    recently-used item although it does not change the state of the dict
    itself.

    See also SmallLRUCache (below), which is faster in some cases.
    """
    class ItemIterator:
        def __init__(self, c):
            self.c = c
            self.i = c.d[c.hs][2]
        def __iter__(self):
            return self
        def next(self):
            if self.i is self.c.ts:
                raise StopIteration
            k = self.i
            precondition(self.c.d.has_key(k), "The iterated LRUCache doesn't have the next key.  Most likely this is because someone altered the contents of the LRUCache while the iteration was in progress.", k, self.c)
            (v, p, n,) = self.c.d[k]
            self.i = n
            return (k, v,)

    class KeyIterator:
        def __init__(self, c):
            self.c = c
            self.i = c.d[c.hs][2]
        def __iter__(self):
            return self
        def next(self):
            if self.i is self.c.ts:
                raise StopIteration
            k = self.i
            precondition(self.c.d.has_key(k), "The iterated LRUCache doesn't have the next key.  Most likely this is because someone altered the contents of the LRUCache while the iteration was in progress.", k, self.c)
            (v, p, n,) = self.c.d[k]
            self.i = n
            return k

    class ValIterator:
        def __init__(self, c):
            self.c = c
            self.i = c.d[c.hs][2]
        def __iter__(self):
            return self
        def next(self):
            if self.i is self.c.ts:
                raise StopIteration
            precondition(self.c.d.has_key(self.i), "The iterated LRUCache doesn't have the next key.  Most likely this is because someone altered the contents of the LRUCache while the iteration was in progress.", self.i, self.c)
            (v, p, n,) = self.c.d[self.i]
            self.i = n
            return v

    class Sentinel:
        def __init__(self, msg):
            self.msg = msg
        def __repr__(self):
            return "<%s %s>" % (self.__class__.__name__, self.msg,)

    def __init__(self, initialdata={}, maxsize=128):
        precondition(maxsize > 0)
        self.m = maxsize+2 # The +2 is for the head and tail nodes.
        self.d = {} # k: k, v: [v, prev, next,] # the dict
        self.hs = LRUCache.Sentinel("hs")
        self.ts = LRUCache.Sentinel("ts")
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
        _assert(len(self.d) <= self.m, "Size is required to be <= maxsize.", len(self.d), self.m)
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
            _assert(k not in (self.hs, self.ts,))
            count += 1
        _assert(count == len(self.d)-2, count, len(self.d)) # -2 for the sentinels

        return True

    def freshen(self, k, strictkey=False):
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
        return LRUCache.ItemIterator(self)

    def itervalues(self):
        return LRUCache.ValIterator(self)

    def iterkeys(self):
        return self.__iter__()

    def __iter__(self):
        return LRUCache.KeyIterator(self)

    def __getitem__(self, key, default=None, strictkey=True):
        node = self.d.get(key)
        if not node:
            if strictkey:
                raise KeyError, key
            return default
        self.freshen(key)
        return node[0]

    def __setitem__(self, k, v=None):
        assert self._assert_invariants()

        node = self.d.get(k)
        if node:
            node[0] = v
            self.freshen(k)
            return

        if len(self.d) == self.m:
            # If this insert is going to increase the size of the cache to
            # bigger than maxsize.
            self.pop()

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
            self.freshen(key)
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

        if len(otherdict) >= (self.m-2): # -2 for the sentinel nodes
            # optimization
            self.clear()
            assert self._assert_invariants()

            i = otherdict.iteritems()
            try:
                while len(self.d) < self.m:
                    (k, v,) = i.next()
                    assert self._assert_invariants()
                    self[k] = v
                    assert self._assert_invariants()
                return self
            except StopIteration:
                _assert(False, "Internal error -- this should never have happened since the while loop should have terminated first.")
                return self

        for (k, v,) in otherdict.iteritems():
            assert self._assert_invariants()
            self[k] = v
            assert self._assert_invariants()

    def pop(self):
        assert self._assert_invariants()
        if len(self.d) < 2: # the +2 is for the sentinels
            raise KeyError, 'popitem(): dictionary is empty'
        k = self.d[self.ts][1]
        self.remove(k)
        assert self._assert_invariants()
        return k

    def popitem(self):
        assert self._assert_invariants()
        if len(self.d) < 2: # the +2 is for the sentinels
            raise KeyError, 'popitem(): dictionary is empty'
        k = self.d[self.ts][1]
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

class SmallLRUCache(dict):
    """
    SmallLRUCache is faster than LRUCache for small sets.  How small?  That
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
            precondition(self.i <= len(self.c._lru), "The iterated SmallLRUCache doesn't have this many elements.  Most likely this is because someone altered the contents of the LRUCache while the iteration was in progress.", self.i, self.c)
            precondition(dict.has_key(self.c, self.c._lru[self.i]), "The iterated SmallLRUCache doesn't have this key.  Most likely this is because someone altered the contents of the LRUCache while the iteration was in progress.", self.i, self.c._lru[self.i], self.c)
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
            precondition(self.i <= len(self.c._lru), "The iterated SmallLRUCache doesn't have this many elements.  Most likely this is because someone altered the contents of the LRUCache while the iteration was in progress.", self.i, self.c)
            precondition(dict.has_key(self.c, self.c._lru[self.i]), "The iterated SmallLRUCache doesn't have this key.  Most likely this is because someone altered the contents of the LRUCache while the iteration was in progress.", self.i, self.c._lru[self.i], self.c)
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
            precondition(self.i <= len(self.c._lru), "The iterated SmallLRUCache doesn't have this many elements.  Most likely this is because someone altered the contents of the LRUCache while the iteration was in progress.", self.i, self.c)
            precondition(dict.has_key(self.c, self.c._lru[self.i]), "The iterated SmallLRUCache doesn't have this key.  Most likely this is because someone altered the contents of the LRUCache while the iteration was in progress.", self.i, self.c._lru[self.i], self.c)
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

class LinkedListLRUCache:
    """
    This is slower and less featureful than LRUCache.  It is included
    here for comparison purposes.

    Implementation of a length-limited O(1) LRU queue.
    Built for and used by PyPE:
    http://pype.sourceforge.net
    original Copyright 2003 Josiah Carlson.
    useful methods and _assert_invariant added by Zooko for testing and benchmarking purposes
    """
    class Node:
        def __init__(self, prev, me):
            self.prev = prev
            self.me = me
            self.next = None
    def __init__(self, initialdata={}, maxsize=128):
        self._maxsize = max(maxsize, 1)
        self.d = {}
        self.first = None
        self.last = None
        for key, value in initialdata.iteritems():
            self[key] = value
    def clear(self):
        self.d = {}
        self.first = None
        self.last = None
    def update(self, otherdict):
        for (k, v,) in otherdict.iteritems():
            self[k] = v
    def setdefault(self, key, default=None):
        if not self.has_key(key):
            self[key] = default
        return self[key]
    def _assert_invariants(self):
        def lliterkeys(self):
            cur = self.first
            while cur != None:
                cur2 = cur.next
                yield cur.me[0]
                cur = cur2
        def lllen(self):
            # Ugh.
            acc = 0
            for x in lliterkeys(self):
                acc += 1
            return acc
        def llhaskey(self, key):
            # Ugh.
            for x in lliterkeys(self):
                if x is key:
                    return True
            return False
        for k in lliterkeys(self):
            _assert(self.d.has_key(k), "Each key in the linked list is required to be in the dict.", k)
        for k in self.d.iterkeys():
            _assert(llhaskey(self, k), "Each key in the dict is required to be in the linked list.", k)
        _assert(lllen(self) == len(self.d), "internal consistency", self, self.d)
        _assert(len(self.d) <= self._maxsize, "Size is required to be <= maxsize.")
        return True
    def __contains__(self, obj):
        return obj in self.d
    def has_key(self, key):
        return self.__contains__(key)
    def __getitem__(self, obj):
        a = self.d[obj].me
        self[a[0]] = a[1]
        return a[1]
    def get(self, key, default=None, strictkey=False):
        if not self.has_key(key) and strictkey:
            raise KeyError, key
        if self.has_key(key):
            return self.__getitem__(key)
        else:
            return default
    def __setitem__(self, obj, val):
        if obj in self.d:
            del self[obj]
        nobj = self.Node(self.last, (obj, val))
        if self.first is None:
            self.first = nobj
        if self.last:
            self.last.next = nobj
        self.last = nobj
        self.d[obj] = nobj
        if len(self.d) > self._maxsize:
            if self.first == self.last:
                self.first = None
                self.last = None
                return
            a = self.first
            a.next.prev = None
            self.first = a.next
            a.next = None
            del self.d[a.me[0]]
            del a
    def insert(self, key, item=None):
        return self.__setitem__(key, item)
    def __delitem__(self, obj, default=None, strictkey=True):
        if self.d.has_key(obj):
            nobj = self.d[obj]
            if nobj.prev:
                nobj.prev.next = nobj.next
            else:
                self.first = nobj.next
            if nobj.next:
                nobj.next.prev = nobj.prev
            else:
                self.last = nobj.prev
            val = self.d[obj]
            del self.d[obj]
            return val.me[1]
        elif strictkey:
            raise KeyError, obj
        else:
            return default
    def remove(self, obj, default=None, strictkey=True):
        return self.__delitem__(obj, default=default, strictkey=strictkey)
    def __iter__(self):
        cur = self.first
        while cur != None:
            cur2 = cur.next
            yield cur.me[1]
            cur = cur2
    def iteritems(self):
        cur = self.first
        while cur != None:
            cur2 = cur.next
            yield cur.me
            cur = cur2
    def iterkeys(self):
        return iter(self.d)
    def itervalues(self):
        for i,j in self.iteritems():
            yield j
    def values(self):
        l = []
        for v in self.itervalues():
            l.append(v)
        return l
    def keys(self):
        return self.d.keys()
    def __len__(self):
        return self.d.__len__()
    def popitem(self):
        i = self.last.me
        obj = self.remove(i[0])
        return obj

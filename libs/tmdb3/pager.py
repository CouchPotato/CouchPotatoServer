#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-----------------------
# Name: pager.py    List-like structure designed for handling paged results
# Python Library
# Author: Raymond Wagner
#-----------------------

from collections import Sequence, Iterator


class PagedIterator(Iterator):
    def __init__(self, parent):
        self._parent = parent
        self._index = -1
        self._len = len(parent)

    def __iter__(self):
        return self

    def next(self):
        self._index += 1
        if self._index == self._len:
            raise StopIteration
        return self._parent[self._index]


class UnpagedData(object):
    def copy(self):
        return self.__class__()

    def __mul__(self, other):
        return (self.copy() for a in range(other))

    def __rmul__(self, other):
        return (self.copy() for a in range(other))


class PagedList(Sequence):
    """
    List-like object, with support for automatically grabbing
    additional pages from a data source.
    """
    _iter_class = None

    def __iter__(self):
        if self._iter_class is None:
            self._iter_class = type(self.__class__.__name__ + 'Iterator',
                                    (PagedIterator,), {})
        return self._iter_class(self)

    def __len__(self):
        try:
            return self._len
        except:
            return len(self._data)

    def __init__(self, iterable, pagesize=20):
        self._data = list(iterable)
        self._pagesize = pagesize

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[x] for x in xrange(*index.indices(len(self)))]
        if index >= len(self):
            raise IndexError("list index outside range")
        if (index >= len(self._data)) \
                or isinstance(self._data[index], UnpagedData):
            self._populatepage(index/self._pagesize + 1)
        return self._data[index]

    def __setitem__(self, index, value):
        raise NotImplementedError

    def __delitem__(self, index):
        raise NotImplementedError

    def __contains__(self, item):
        raise NotImplementedError

    def _populatepage(self, page):
        pagestart = (page-1) * self._pagesize
        if len(self._data) < pagestart:
            self._data.extend(UnpagedData()*(pagestart-len(self._data)))
        if len(self._data) == pagestart:
            self._data.extend(self._getpage(page))
        else:
            for data in self._getpage(page):
                self._data[pagestart] = data
                pagestart += 1

    def _getpage(self, page):
        raise NotImplementedError("PagedList._getpage() must be provided " +
                                  "by subclass")


class PagedRequest(PagedList):
    """
    Derived PageList that provides a list-like object with automatic
    paging intended for use with search requests.
    """
    def __init__(self, request, handler=None):
        self._request = request
        if handler:
            self._handler = handler
        super(PagedRequest, self).__init__(self._getpage(1), 20)

    def _getpage(self, page):
        req = self._request.new(page=page)
        res = req.readJSON()
        self._len = res['total_results']
        for item in res['results']:
            if item is None:
                yield None
            else:
                yield self._handler(item)

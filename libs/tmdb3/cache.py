#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-----------------------
# Name: cache.py
# Python Library
# Author: Raymond Wagner
# Purpose: Caching framework to store TMDb API results
#-----------------------

import time
import os

from tmdb_exceptions import *
from cache_engine import Engines

import cache_null
import cache_file


class Cache(object):
    """
    This class implements a cache framework, allowing selecting of a
    pluggable engine. The framework stores data in a key/value manner,
    along with a lifetime, after which data will be expired and
    pulled fresh next time it is requested from the cache.

    This class defines a wrapper to be used with query functions. The
    wrapper will automatically cache the inputs and outputs of the
    wrapped function, pulling the output from local storage for
    subsequent calls with those inputs.
    """
    def __init__(self, engine=None, *args, **kwargs):
        self._engine = None
        self._data = {}
        self._age = 0
        self.configure(engine, *args, **kwargs)

    def _import(self, data=None):
        if data is None:
            data = self._engine.get(self._age)
        for obj in sorted(data, key=lambda x: x.creation):
            if not obj.expired:
                self._data[obj.key] = obj
                self._age = max(self._age, obj.creation)

    def _expire(self):
        for k, v in self._data.items():
            if v.expired:
                del self._data[k]

    def configure(self, engine, *args, **kwargs):
        if engine is None:
            engine = 'file'
        elif engine not in Engines:
            raise TMDBCacheError("Invalid cache engine specified: "+engine)
        self._engine = Engines[engine](self)
        self._engine.configure(*args, **kwargs)

    def put(self, key, data, lifetime=60*60*12):
        # pull existing data, so cache will be fresh when written back out
        if self._engine is None:
            raise TMDBCacheError("No cache engine configured")
        self._expire()
        self._import(self._engine.put(key, data, lifetime))

    def get(self, key):
        if self._engine is None:
            raise TMDBCacheError("No cache engine configured")
        self._expire()
        if key not in self._data:
            self._import()
        try:
            return self._data[key].data
        except:
            return None

    def cached(self, callback):
        """
        Returns a decorator that uses a callback to specify the key to use
        for caching the responses from the decorated function.
        """
        return self.Cached(self, callback)

    class Cached( object ):
        def __init__(self, cache, callback, func=None, inst=None):
            self.cache = cache
            self.callback = callback
            self.func = func
            self.inst = inst

            if func:
                self.__module__ = func.__module__
                self.__name__ = func.__name__
                self.__doc__ = func.__doc__

        def __call__(self, *args, **kwargs):
            if self.func is None:
                # decorator is waiting to be given a function
                if len(kwargs) or (len(args) != 1):
                    raise TMDBCacheError(
                        'Cache.Cached decorator must be called a single ' +
                        'callable argument before it be used.')
                elif args[0] is None:
                    raise TMDBCacheError(
                        'Cache.Cached decorator called before being given ' +
                        'a function to wrap.')
                elif not callable(args[0]):
                    raise TMDBCacheError(
                        'Cache.Cached must be provided a callable object.')
                return self.__class__(self.cache, self.callback, args[0])
            elif self.inst.lifetime == 0:
                # lifetime of zero means never cache
                return self.func(*args, **kwargs)
            else:
                key = self.callback()
                data = self.cache.get(key)
                if data is None:
                    data = self.func(*args, **kwargs)
                    if hasattr(self.inst, 'lifetime'):
                        self.cache.put(key, data, self.inst.lifetime)
                    else:
                        self.cache.put(key, data)
                return data

        def __get__(self, inst, owner):
            if inst is None:
                return self
            func = self.func.__get__(inst, owner)
            callback = self.callback.__get__(inst, owner)
            return self.__class__(self.cache, callback, func, inst)

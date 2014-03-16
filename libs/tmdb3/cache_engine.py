#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-----------------------
# Name: cache_engine.py
# Python Library
# Author: Raymond Wagner
# Purpose: Base cache engine class for collecting registered engines
#-----------------------

import time
from weakref import ref


class Engines(object):
    """
    Static collector for engines to register against.
    """
    def __init__(self):
        self._engines = {}

    def register(self, engine):
        self._engines[engine.__name__] = engine
        self._engines[engine.name] = engine

    def __getitem__(self, key):
        return self._engines[key]

    def __contains__(self, key):
        return self._engines.__contains__(key)

Engines = Engines()


class CacheEngineType(type):
    """
    Cache Engine Metaclass that registers new engines against the cache
    for named selection and use.
    """
    def __init__(cls, name, bases, attrs):
        super(CacheEngineType, cls).__init__(name, bases, attrs)
        if name != 'CacheEngine':
            # skip base class
            Engines.register(cls)


class CacheEngine(object):
    __metaclass__ = CacheEngineType
    name = 'unspecified'

    def __init__(self, parent):
        self.parent = ref(parent)

    def configure(self):
        raise RuntimeError
    def get(self, date):
        raise RuntimeError
    def put(self, key, value, lifetime):
        raise RuntimeError
    def expire(self, key):
        raise RuntimeError


class CacheObject(object):
    """
    Cache object class, containing one stored record.
    """

    def __init__(self, key, data, lifetime=0, creation=None):
        self.key = key
        self.data = data
        self.lifetime = lifetime
        self.creation = creation if creation is not None else time.time()

    def __len__(self):
        return len(self.data)

    @property
    def expired(self):
        return self.remaining == 0

    @property
    def remaining(self):
        return max((self.creation + self.lifetime) - time.time(), 0)


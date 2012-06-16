# -*- coding: utf-8 -*-
# Copyright 2012 Nicolas Wack <wackou@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
from collections import defaultdict
from functools import wraps
import logging
import os.path
import threading
try:
    import cPickle as pickle
except ImportError:
    import pickle


__all__ = ['Cache', 'cachedmethod']
logger = logging.getLogger(__name__)


class Cache(object):
    """A Cache object contains cached values for methods. It can have
    separate internal caches, one for each service

    """
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.cache = defaultdict(dict)
        self.lock = threading.RLock()

    def __del__(self):
        for service_name in self.cache:
            self.save(service_name)

    def cache_location(self, service_name):
        return os.path.join(self.cache_dir, 'subliminal_%s.cache' % service_name)

    def load(self, service_name):
        with self.lock:
            if service_name in self.cache:
                # already loaded
                return

            self.cache[service_name] = defaultdict(dict)
            filename = self.cache_location(service_name)
            logger.debug(u'Cache: loading cache from %s' % filename)
            try:
                self.cache[service_name] = pickle.load(open(filename, 'rb'))
            except IOError:
                logger.info('Cache: Cache file "%s" doesn\'t exist, creating it' % filename)
            except EOFError:
                logger.error('Cache: cache file "%s" is corrupted... Removing it.' % filename)
                os.remove(filename)

    def save(self, service_name):
        filename = self.cache_location(service_name)
        logger.debug(u'Cache: saving cache to %s' % filename)
        with self.lock:
            pickle.dump(self.cache[service_name], open(filename, 'wb'))

    def clear(self, service_name):
        try:
            os.remove(self.cache_location(service_name))
        except OSError:
            pass
        self.cache[service_name] = defaultdict(dict)

    def cached_func_key(self, func, cls=None):
        try:
            cls = func.im_class
        except:
            pass
        return ('%s.%s' % (cls.__module__, cls.__name__), func.__name__)

    def function_cache(self, service_name, func):
        func_key = self.cached_func_key(func)
        return self.cache[service_name][func_key]

    def cache_for(self, service_name, func, args, result):
        # no need to lock here, dict ops are atomic
        self.function_cache(service_name, func)[args] = result

    def cached_value(self, service_name, func, args):
        """Raises KeyError if not found"""
        # no need to lock here, dict ops are atomic
        return self.function_cache(service_name, func)[args]


def cachedmethod(function):
    """Decorator to make a method use the cache.

    .. note::

        This can NOT be used with static functions, it has to be used on
        methods of some class

    """
    @wraps(function)
    def cached(*args):
        c = args[0].config.cache
        service_name = args[0].__class__.__name__
        func_key = c.cached_func_key(function, cls=args[0].__class__)
        func_cache = c.cache[service_name][func_key]

        # we need to remove the first element of args for the key, as it is the
        # instance pointer and we don't want the cache to know which instance
        # called it, it is shared among all instances of the same class
        key = args[1:]

        if key in func_cache:
            result = func_cache[key]
            logger.debug(u'Using cached value for %s(%s), returns: %s' % (func_key, key, result))
            return result

        result = function(*args)

        # note: another thread could have already cached a value in the
        # meantime, but that's ok as we prefer to keep the latest value in
        # the cache
        func_cache[key] = result
        return result
    return cached

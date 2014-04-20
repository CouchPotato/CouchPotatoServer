#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011-2013 Codernity (http://codernity.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import functools
from heapq import nsmallest
from operator import itemgetter
from collections import defaultdict


try:
    from collections import Counter
except ImportError:
    class Counter(dict):
        'Mapping where default values are zero'
        def __missing__(self, key):
            return 0


def twolvl_iterator(dict):
    for k, v in dict.iteritems():
        for kk, vv in v.iteritems():
            yield k, kk, vv


def create_cache1lvl(lock_obj):
    def cache1lvl(maxsize=100):
        """
        modified version of http://code.activestate.com/recipes/498245/
        """
        def decorating_function(user_function):
            cache = {}
            use_count = Counter()
            lock = lock_obj()

            @functools.wraps(user_function)
            def wrapper(key, *args, **kwargs):
                try:
                    result = cache[key]
                except KeyError:
                    with lock:
                        if len(cache) == maxsize:
                            for k, _ in nsmallest(maxsize // 10 or 1,
                                                  use_count.iteritems(),
                                                  key=itemgetter(1)):
                                del cache[k], use_count[k]
                        cache[key] = user_function(key, *args, **kwargs)
                        result = cache[key]
                        use_count[key] += 1
                else:
                    with lock:
                        use_count[key] += 1
                return result

            def clear():
                cache.clear()
                use_count.clear()

            def delete(key):
                try:
                    del cache[key]
                    del use_count[key]
                    return True
                except KeyError:
                    return False

            wrapper.clear = clear
            wrapper.cache = cache
            wrapper.delete = delete
            return wrapper
        return decorating_function
    return cache1lvl


def create_cache2lvl(lock_obj):
    def cache2lvl(maxsize=100):
        """
        modified version of http://code.activestate.com/recipes/498245/
        """
        def decorating_function(user_function):
            cache = {}
            use_count = defaultdict(Counter)
            lock = lock_obj()

            @functools.wraps(user_function)
            def wrapper(*args, **kwargs):
                try:
                    result = cache[args[0]][args[1]]
                except KeyError:
                    with lock:
                        if wrapper.cache_size == maxsize:
                            to_delete = maxsize / 10 or 1
                            for k1, k2, v in nsmallest(to_delete,
                                                       twolvl_iterator(
                                                           use_count),
                                                       key=itemgetter(2)):
                                del cache[k1][k2], use_count[k1][k2]
                                if not cache[k1]:
                                    del cache[k1]
                                    del use_count[k1]
                            wrapper.cache_size -= to_delete
                        result = user_function(*args, **kwargs)
                        try:
                            cache[args[0]][args[1]] = result
                        except KeyError:
                            cache[args[0]] = {args[1]: result}
                        use_count[args[0]][args[1]] += 1
                        wrapper.cache_size += 1
                else:
                    use_count[args[0]][args[1]] += 1
                return result

            def clear():
                cache.clear()
                use_count.clear()

            def delete(key, *args):
                if args:
                    try:
                        del cache[key][args[0]]
                        del use_count[key][args[0]]
                        if not cache[key]:
                            del cache[key]
                            del use_count[key]
                        wrapper.cache_size -= 1
                        return True
                    except KeyError:
                        return False
                else:
                    try:
                        wrapper.cache_size -= len(cache[key])
                        del cache[key]
                        del use_count[key]
                        return True
                    except KeyError:
                        return False

            wrapper.clear = clear
            wrapper.cache = cache
            wrapper.delete = delete
            wrapper.cache_size = 0
            return wrapper
        return decorating_function
    return cache2lvl

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


from CodernityDB.misc import NONE


def __patch(obj, name, new):
    n = NONE()
    orig = getattr(obj, name, n)
    if orig is not n:
        if orig == new:
            raise Exception("Shouldn't happen, new and orig are the same")
        setattr(obj, name, new)
    return


def patch_cache_lfu(lock_obj):
    """
    Patnches cache mechanizm to be thread safe (gevent ones also)

    .. note::

       It's internal CodernityDB mechanizm, it will be called when needed

    """
    import lfu_cache
    import lfu_cache_with_lock
    lfu_lock1lvl = lfu_cache_with_lock.create_cache1lvl(lock_obj)
    lfu_lock2lvl = lfu_cache_with_lock.create_cache2lvl(lock_obj)
    __patch(lfu_cache, 'cache1lvl', lfu_lock1lvl)
    __patch(lfu_cache, 'cache2lvl', lfu_lock2lvl)


def patch_cache_rr(lock_obj):
    """
    Patches cache mechanizm to be thread safe (gevent ones also)

    .. note::

       It's internal CodernityDB mechanizm, it will be called when needed

    """
    import rr_cache
    import rr_cache_with_lock
    rr_lock1lvl = rr_cache_with_lock.create_cache1lvl(lock_obj)
    rr_lock2lvl = rr_cache_with_lock.create_cache2lvl(lock_obj)
    __patch(rr_cache, 'cache1lvl', rr_lock1lvl)
    __patch(rr_cache, 'cache2lvl', rr_lock2lvl)


def patch_flush_fsync(db_obj):
    """
    Will always execute index.fsync after index.flush.

    .. note::

       It's for advanced users, use when you understand difference between `flush` and `fsync`, and when you definitely need that.

    It's important to call it **AFTER** database has all indexes etc (after db.create or db.open)

    Example usage::

        ...
        db = Database('/tmp/patch_demo')
        db.create()
        patch_flush_fsync(db)
        ...

    """

    def always_fsync(ind_obj):
        def _inner():
            ind_obj.orig_flush()
            ind_obj.fsync()
        return _inner

    for index in db_obj.indexes:
        setattr(index, 'orig_flush', index.flush)
        setattr(index, 'flush', always_fsync(index))

    setattr(db_obj, 'orig_flush', db_obj.flush)
    setattr(db_obj, 'flush', always_fsync(db_obj))

    return

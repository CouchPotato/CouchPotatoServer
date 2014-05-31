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

from CodernityDB.env import cdb_environment
from CodernityDB.database import PreconditionsException, RevConflict, Database
# from database import Database

from collections import defaultdict
from functools import wraps
from types import MethodType


class th_safe_gen:

    def __init__(self, name, gen, l=None):
        self.lock = l
        self.__gen = gen
        self.name = name

    def __iter__(self):
        return self

    def next(self):
        with self.lock:
            return self.__gen.next()

    @staticmethod
    def wrapper(method, index_name, meth_name, l=None):
        @wraps(method)
        def _inner(*args, **kwargs):
            res = method(*args, **kwargs)
            return th_safe_gen(index_name + "_" + meth_name, res, l)
        return _inner


def safe_wrapper(method, lock):
    @wraps(method)
    def _inner(*args, **kwargs):
        with lock:
            return method(*args, **kwargs)
    return _inner


class SafeDatabase(Database):

    def __init__(self, path, *args, **kwargs):
        super(SafeDatabase, self).__init__(path, *args, **kwargs)
        self.indexes_locks = defaultdict(
            lambda: cdb_environment['rlock_obj']())
        self.close_open_lock = cdb_environment['rlock_obj']()
        self.main_lock = cdb_environment['rlock_obj']()
        self.id_revs = {}

    def __patch_index_gens(self, name):
        ind = self.indexes_names[name]
        for c in ('all', 'get_many'):
            m = getattr(ind, c)
            if getattr(ind, c + "_orig", None):
                return
            m_fixed = th_safe_gen.wrapper(m, name, c, self.indexes_locks[name])
            setattr(ind, c, m_fixed)
            setattr(ind, c + '_orig', m)

    def __patch_index_methods(self, name):
        ind = self.indexes_names[name]
        lock = self.indexes_locks[name]
        for curr in dir(ind):
            meth = getattr(ind, curr)
            if not curr.startswith('_') and isinstance(meth, MethodType):
                setattr(ind, curr, safe_wrapper(meth, lock))
        stor = ind.storage
        for curr in dir(stor):
            meth = getattr(stor, curr)
            if not curr.startswith('_') and isinstance(meth, MethodType):
                setattr(stor, curr, safe_wrapper(meth, lock))

    def __patch_index(self, name):
        self.__patch_index_methods(name)
        self.__patch_index_gens(name)

    def initialize(self, *args, **kwargs):
        with self.close_open_lock:
            self.close_open_lock.acquire()
            res = super(SafeDatabase, self).initialize(*args, **kwargs)
            for name in self.indexes_names.iterkeys():
                self.indexes_locks[name] = cdb_environment['rlock_obj']()
            return res

    def open(self, *args, **kwargs):
        with self.close_open_lock:
            res = super(SafeDatabase, self).open(*args, **kwargs)
            for name in self.indexes_names.iterkeys():
                self.indexes_locks[name] = cdb_environment['rlock_obj']()
                self.__patch_index(name)
            return res

    def create(self, *args, **kwargs):
        with self.close_open_lock:
            res = super(SafeDatabase, self).create(*args, **kwargs)
            for name in self.indexes_names.iterkeys():
                self.indexes_locks[name] = cdb_environment['rlock_obj']()
                self.__patch_index(name)
            return res

    def close(self):
        with self.close_open_lock:
            return super(SafeDatabase, self).close()

    def destroy(self):
        with self.close_open_lock:
            return super(SafeDatabase, self).destroy()

    def add_index(self, *args, **kwargs):
        with self.main_lock:
            res = super(SafeDatabase, self).add_index(*args, **kwargs)
            if self.opened:
                self.indexes_locks[res] = cdb_environment['rlock_obj']()
                self.__patch_index(res)
            return res

    def _single_update_index(self, index, data, db_data, doc_id):
        with self.indexes_locks[index.name]:
            super(SafeDatabase, self)._single_update_index(
                index, data, db_data, doc_id)

    def _single_delete_index(self, index, data, doc_id, old_data):
        with self.indexes_locks[index.name]:
            super(SafeDatabase, self)._single_delete_index(
                index, data, doc_id, old_data)

    def edit_index(self, *args, **kwargs):
        with self.main_lock:
            res = super(SafeDatabase, self).edit_index(*args, **kwargs)
            if self.opened:
                self.indexes_locks[res] = cdb_environment['rlock_obj']()
                self.__patch_index(res)
            return res

    def set_indexes(self, *args, **kwargs):
        try:
            self.main_lock.acquire()
            super(SafeDatabase, self).set_indexes(*args, **kwargs)
        finally:
            self.main_lock.release()

    def reindex_index(self, index, *args, **kwargs):
        if isinstance(index, basestring):
            if not index in self.indexes_names:
                raise PreconditionsException("No index named %s" % index)
            index = self.indexes_names[index]
        key = index.name + "reind"
        self.main_lock.acquire()
        if key in self.indexes_locks:
            lock = self.indexes_locks[index.name + "reind"]
        else:
            self.indexes_locks[index.name +
                               "reind"] = cdb_environment['rlock_obj']()
            lock = self.indexes_locks[index.name + "reind"]
        self.main_lock.release()
        try:
            lock.acquire()
            super(SafeDatabase, self).reindex_index(
                index, *args, **kwargs)
        finally:
            lock.release()

    def flush(self):
        try:
            self.main_lock.acquire()
            super(SafeDatabase, self).flush()
        finally:
            self.main_lock.release()

    def fsync(self):
        try:
            self.main_lock.acquire()
            super(SafeDatabase, self).fsync()
        finally:
            self.main_lock.release()

    def _update_id_index(self, _rev, data):
        with self.indexes_locks['id']:
            return super(SafeDatabase, self)._update_id_index(_rev, data)

    def _delete_id_index(self, _id, _rev, data):
        with self.indexes_locks['id']:
            return super(SafeDatabase, self)._delete_id_index(_id, _rev, data)

    def _update_indexes(self, _rev, data):
        _id, new_rev, db_data = self._update_id_index(_rev, data)
        with self.main_lock:
            self.id_revs[_id] = new_rev
        for index in self.indexes[1:]:
            with self.main_lock:
                curr_rev = self.id_revs.get(_id)  # get last _id, _rev
                if curr_rev != new_rev:
                    break  # new update on the way stop current
            self._single_update_index(index, data, db_data, _id)
        with self.main_lock:
            if self.id_revs[_id] == new_rev:
                del self.id_revs[_id]
        return _id, new_rev

    def _delete_indexes(self, _id, _rev, data):
        old_data = self.get('id', _id)
        if old_data['_rev'] != _rev:
            raise RevConflict()
        with self.main_lock:
            self.id_revs[_id] = _rev
        for index in self.indexes[1:]:
            self._single_delete_index(index, data, _id, old_data)
        self._delete_id_index(_id, _rev, data)
        with self.main_lock:
            if self.id_revs[_id] == _rev:
                del self.id_revs[_id]

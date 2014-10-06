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


from CodernityDB3.hash_index import UniqueHashIndex, HashIndex
from CodernityDB3.sharded_index import ShardedIndex
from CodernityDB3.index import IndexPreconditionsException

from random import getrandbits
import uuid


class IU_ShardedUniqueHashIndex(ShardedIndex):

    custom_header = """import uuid
from random import getrandbits
from CodernityDB3.sharded_index import ShardedIndex
"""

    def __init__(self, db_path, name, *args, **kwargs):
        if kwargs.get('sh_nums', 0) > 255:
            raise IndexPreconditionsException("Too many shards")
        kwargs['ind_class'] = UniqueHashIndex
        super(IU_ShardedUniqueHashIndex, self).__init__(db_path,
                                                        name, *args, **kwargs)
        self.patchers.append(self.wrap_insert_id_index)

    @staticmethod
    def wrap_insert_id_index(db_obj, clean=False):
        def _insert_id_index(_rev, data):
            """
            Performs insert on **id** index.
            """
            _id, value = db_obj.id_ind.make_key_value(data)  # may be improved
            trg_shard = _id[:2]
            storage = db_obj.id_ind.shards_r[trg_shard].storage
            start, size = storage.insert(value)
            db_obj.id_ind.insert(_id, _rev, start, size)
            return _id
        if not clean:
            if hasattr(db_obj, '_insert_id_index_orig'):
                raise IndexPreconditionsException(
                    "Already patched, something went wrong")
            setattr(db_obj, "_insert_id_index_orig", db_obj._insert_id_index)
            setattr(db_obj, "_insert_id_index", _insert_id_index)
        else:
            setattr(db_obj, "_insert_id_index", db_obj._insert_id_index_orig)
            delattr(db_obj, "_insert_id_index_orig")

    def create_key(self):
        h = uuid.UUID(int=getrandbits(128), version=4).hex
        trg = self.last_used + 1
        if trg >= self.sh_nums:
            trg = 0
        self.last_used = trg
        h = '%02x%30s' % (trg, h[2:])
        return h

    def delete(self, key, *args, **kwargs):
        trg_shard = key[:2]
        op = self.shards_r[trg_shard]
        return op.delete(key, *args, **kwargs)

    def update(self, key, *args, **kwargs):
        trg_shard = key[:2]
        self.last_used = int(trg_shard, 16)
        op = self.shards_r[trg_shard]
        return op.update(key, *args, **kwargs)

    def insert(self, key, *args, **kwargs):
        trg_shard = key[:2]  # in most cases it's in create_key BUT not always
        self.last_used = int(key[:2], 16)
        op = self.shards_r[trg_shard]
        return op.insert(key, *args, **kwargs)

    def get(self, key, *args, **kwargs):
        trg_shard = key[:2]
        self.last_used = int(trg_shard, 16)
        op = self.shards_r[trg_shard]
        return op.get(key, *args, **kwargs)


class ShardedUniqueHashIndex(IU_ShardedUniqueHashIndex):

    # allow unique hash to be used directly
    custom_header = 'from CodernityDB3.sharded_hash import IU_ShardedUniqueHashIndex'

    pass


class IU_ShardedHashIndex(ShardedIndex):

    custom_header = """from CodernityDB3.sharded_index import ShardedIndex"""

    def __init__(self, db_path, name, *args, **kwargs):
        kwargs['ind_class'] = HashIndex
        super(IU_ShardedHashIndex, self).__init__(db_path, name, *
                                                  args, **kwargs)

    def calculate_shard(self, key):
        """
        Must be implemented. It has to return shard to be used by key

        :param key: key
        :returns: target shard
        :rtype: int
        """
        raise NotImplementedError()

    def delete(self, doc_id, key, *args, **kwargs):
        trg_shard = self.calculate_shard(key)
        op = self.shards_r[trg_shard]
        return op.delete(doc_id, key, *args, **kwargs)

    def insert(self, doc_id, key, *args, **kwargs):
        trg_shard = self.calculate_shard(key)
        op = self.shards_r[trg_shard]
        return op.insert(doc_id, key, *args, **kwargs)

    def update(self, doc_id, key, *args, **kwargs):
        trg_shard = self.calculate_shard(key)
        op = self.shards_r[trg_shard]
        return op.insert(doc_id, key, *args, **kwargs)

    def get(self, key, *args, **kwargs):
        trg_shard = self.calculate_shard(key)
        op = self.shards_r[trg_shard]
        return op.get(key, *args, **kwargs)


class ShardedHashIndex(IU_ShardedHashIndex):
    pass

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


from CodernityDB.index import Index
# from CodernityDB.env import cdb_environment
# import warnings


class ShardedIndex(Index):

    def __init__(self, db_path, name, *args, **kwargs):
        """
        There are 3 additional parameters. You have to hardcode them in your custom class. **NEVER** use directly

        :param int sh_nums: how many shards should be
        :param class ind_class: Index class to use (HashIndex or your custom one)
        :param bool use_make_keys: if True, `make_key`, and `make_key_value` will be overriden with those from first shard

        The rest parameters are passed straight to `ind_class` shards.

        """
        super(ShardedIndex, self).__init__(db_path, name)
        try:
            self.sh_nums = kwargs.pop('sh_nums')
        except KeyError:
            self.sh_nums = 5
        try:
            ind_class = kwargs.pop('ind_class')
        except KeyError:
            raise Exception("ind_class must be given")
        else:
            # if not isinstance(ind_class, basestring):
            #     ind_class = ind_class.__name__
            self.ind_class = ind_class
        if 'use_make_keys' in kwargs:
            self.use_make_keys = kwargs.pop('use_make_keys')
        else:
            self.use_make_keys = False
        self._set_shard_datas(*args, **kwargs)
        self.patchers = []  # database object patchers

    def _set_shard_datas(self, *args, **kwargs):
        self.shards = {}
        self.shards_r = {}
#        ind_class = globals()[self.ind_class]
        ind_class = self.ind_class
        i = 0
        for sh_name in [self.name + str(x) for x in xrange(self.sh_nums)]:
            # dict is better than list in that case
            self.shards[i] = ind_class(self.db_path, sh_name, *args, **kwargs)
            self.shards_r['%02x' % i] = self.shards[i]
            self.shards_r[i] = self.shards[i]
            i += 1

        if not self.use_make_keys:
            self.make_key = self.shards[0].make_key
            self.make_key_value = self.shards[0].make_key_value

        self.last_used = 0

    @property
    def storage(self):
        st = self.shards[self.last_used].storage
        return st

    def __getattr__(self, name):
        return getattr(self.shards[self.last_used], name)

    def open_index(self):
        for curr in self.shards.itervalues():
            curr.open_index()

    def create_index(self):
        for curr in self.shards.itervalues():
            curr.create_index()

    def destroy(self):
        for curr in self.shards.itervalues():
            curr.destroy()

    def compact(self):
        for curr in self.shards.itervalues():
            curr.compact()

    def reindex(self):
        for curr in self.shards.itervalues():
            curr.reindex()

    def all(self, *args, **kwargs):
        for curr in self.shards.itervalues():
            for now in curr.all(*args, **kwargs):
                yield now

    def get_many(self, *args, **kwargs):
        for curr in self.shards.itervalues():
            for now in curr.get_many(*args, **kwargs):
                yield now

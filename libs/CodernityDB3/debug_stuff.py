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

from CodernityDB3.tree_index import TreeBasedIndex
import struct
import os

import inspect
from functools import wraps
import json


class DebugTreeBasedIndex(TreeBasedIndex):

    def __init__(self, *args, **kwargs):
        super(DebugTreeBasedIndex, self).__init__(*args, **kwargs)

    def print_tree(self):
        print '-----CURRENT TREE-----'
        print self.root_flag

        if self.root_flag == 'l':
            print '---ROOT---'
            self._print_leaf_data(self.data_start)
            return
        else:
            print '---ROOT---'
            self._print_node_data(self.data_start)
            nr_of_el, children_flag = self._read_node_nr_of_elements_and_children_flag(
                self.data_start)
            nodes = []
            for index in range(nr_of_el):
                l_pointer, key, r_pointer = self._read_single_node_key(
                    self.data_start, index)
                nodes.append(l_pointer)
            nodes.append(r_pointer)
            print 'ROOT NODES', nodes
            while children_flag == 'n':
                self._print_level(nodes, 'n')
                new_nodes = []
                for node in nodes:
                    nr_of_el, children_flag = \
                        self._read_node_nr_of_elements_and_children_flag(node)
                    for index in range(nr_of_el):
                        l_pointer, key, r_pointer = self._read_single_node_key(
                            node, index)
                        new_nodes.append(l_pointer)
                    new_nodes.append(r_pointer)
                nodes = new_nodes
            self._print_level(nodes, 'l')

    def _print_level(self, nodes, flag):
        print '---NEXT LVL---'
        if flag == 'n':
            for node in nodes:
                self._print_node_data(node)
        elif flag == 'l':
            for node in nodes:
                self._print_leaf_data(node)

    def _print_leaf_data(self, leaf_start_position):
        print 'printing data of leaf at', leaf_start_position
        nr_of_elements = self._read_leaf_nr_of_elements(leaf_start_position)
        self.buckets.seek(leaf_start_position)
        data = self.buckets.read(self.leaf_heading_size +
                                 nr_of_elements * self.single_leaf_record_size)
        leaf = struct.unpack('<' + self.leaf_heading_format +
                             nr_of_elements * self.single_leaf_record_format, data)
        print leaf
        print

    def _print_node_data(self, node_start_position):
        print 'printing data of node at', node_start_position
        nr_of_elements = self._read_node_nr_of_elements_and_children_flag(
            node_start_position)[0]
        self.buckets.seek(node_start_position)
        data = self.buckets.read(self.node_heading_size + self.pointer_size
                                 + nr_of_elements * (self.key_size + self.pointer_size))
        node = struct.unpack('<' + self.node_heading_format + self.pointer_format
                             + nr_of_elements * (
                             self.key_format + self.pointer_format),
                             data)
        print node
        print
# ------------------>


def database_step_by_step(db_obj, path=None):

    if not path:
        # ugly for multiplatform support....
        p = db_obj.path
        p1 = os.path.split(p)
        p2 = os.path.split(p1[0])
        p3 = '_'.join([p2[1], 'operation_logger.log'])
        path = os.path.join(os.path.split(p2[0])[0], p3)
    f_obj = open(path, 'wb')

    __stack = []  # inspect.stack() is not working on pytest etc

    def remove_from_stack(name):
        for i in range(len(__stack)):
            if __stack[-i] == name:
                __stack.pop(-i)

    def __dumper(f):
        @wraps(f)
        def __inner(*args, **kwargs):
            funct_name = f.__name__
            if funct_name == 'count':
                name = args[0].__name__
                meth_args = (name,) + args[1:]
            elif funct_name in ('reindex_index', 'compact_index'):
                name = args[0].name
                meth_args = (name,) + args[1:]
            else:
                meth_args = args
            kwargs_copy = kwargs.copy()
            res = None
            __stack.append(funct_name)
            if funct_name == 'insert':
                try:
                    res = f(*args, **kwargs)
                except:
                    packed = json.dumps((funct_name,
                                         meth_args, kwargs_copy, None))
                    f_obj.write('%s\n' % packed)
                    f_obj.flush()
                    raise
                else:
                    packed = json.dumps((funct_name,
                                         meth_args, kwargs_copy, res))
                f_obj.write('%s\n' % packed)
                f_obj.flush()
            else:
                if funct_name == 'get':
                    for curr in __stack:
                        if ('delete' in curr or 'update' in curr) and not curr.startswith('test'):
                            remove_from_stack(funct_name)
                            return f(*args, **kwargs)
                packed = json.dumps((funct_name, meth_args, kwargs_copy))
                f_obj.write('%s\n' % packed)
                f_obj.flush()
                res = f(*args, **kwargs)
            remove_from_stack(funct_name)
            return res
        return __inner

    for meth_name, meth_f in inspect.getmembers(db_obj, predicate=inspect.ismethod):
        if not meth_name.startswith('_'):
            setattr(db_obj, meth_name, __dumper(meth_f))

    setattr(db_obj, 'operation_logger', f_obj)


def database_from_steps(db_obj, path):
    # db_obj.insert=lambda data : insert_for_debug(db_obj, data)
    with open(path, 'rb') as f_obj:
        for current in f_obj:
            line = json.loads(current[:-1])
            if line[0] == 'count':
                obj = getattr(db_obj, line[1][0])
                line[1] = [obj] + line[1][1:]
            name = line[0]
            if name == 'insert':
                try:
                    line[1][0].pop('_rev')
                except:
                    pass
            elif name in ('delete', 'update'):
                el = db_obj.get('id', line[1][0]['_id'])
                line[1][0]['_rev'] = el['_rev']
#                print 'FROM STEPS doing', line
            meth = getattr(db_obj, line[0], None)
            if not meth:
                raise Exception("Method = `%s` not found" % line[0])

            meth(*line[1], **line[2])


# def insert_for_debug(self, data):
#
#    _rev = data['_rev']
#
#    if not '_id' in data:
#        _id = uuid4().hex
#    else:
#        _id = data['_id']
#    data['_id'] = _id
#    try:
#        _id = bytes(_id)
#    except:
#        raise DatabaseException("`_id` must be valid bytes object")
#    self._insert_indexes(_id, _rev, data)
#    ret = {'_id': _id, '_rev': _rev}
#    data.update(ret)
#    return ret

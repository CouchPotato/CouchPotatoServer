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


from index import Index, IndexException, DocIdNotFound, ElemNotFound
import struct
import marshal
import os
import io
import shutil
from storage import IU_Storage
# from ipdb import set_trace

from CodernityDB.env import cdb_environment
from CodernityDB.index import TryReindexException

if cdb_environment.get('rlock_obj'):
    from CodernityDB import patch
    patch.patch_cache_rr(cdb_environment['rlock_obj'])

from CodernityDB.rr_cache import cache1lvl, cache2lvl

tree_buffer_size = io.DEFAULT_BUFFER_SIZE

cdb_environment['tree_buffer_size'] = tree_buffer_size


MODE_FIRST = 0
MODE_LAST = 1

MOVE_BUFFER_PREV = 0
MOVE_BUFFER_NEXT = 1


class NodeCapacityException(IndexException):
    pass


class IU_TreeBasedIndex(Index):

    custom_header = 'from CodernityDB.tree_index import TreeBasedIndex'

    def __init__(self, db_path, name, key_format='32s', pointer_format='I',
                 meta_format='32sIIc', node_capacity=10, storage_class=None):
        if node_capacity < 3:
            raise NodeCapacityException
        super(IU_TreeBasedIndex, self).__init__(db_path, name)
        self.data_start = self._start_ind + 1
        self.node_capacity = node_capacity
        self.flag_format = 'c'
        self.elements_counter_format = 'h'
        self.pointer_format = pointer_format
        self.key_format = key_format
        self.meta_format = meta_format
        self._count_props()
        if not storage_class:
            storage_class = IU_Storage
        if storage_class and not isinstance(storage_class, basestring):
            storage_class = storage_class.__name__
        self.storage_class = storage_class
        self.storage = None
        cache = cache1lvl(100)
        twolvl_cache = cache2lvl(150)
        self._find_key = cache(self._find_key)
        self._match_doc_id = cache(self._match_doc_id)
# self._read_single_leaf_record =
# twolvl_cache(self._read_single_leaf_record)
        self._find_key_in_leaf = twolvl_cache(self._find_key_in_leaf)
        self._read_single_node_key = twolvl_cache(self._read_single_node_key)
        self._find_first_key_occurence_in_node = twolvl_cache(
            self._find_first_key_occurence_in_node)
        self._find_last_key_occurence_in_node = twolvl_cache(
            self._find_last_key_occurence_in_node)
        self._read_leaf_nr_of_elements = cache(self._read_leaf_nr_of_elements)
        self._read_leaf_neighbours = cache(self._read_leaf_neighbours)
        self._read_leaf_nr_of_elements_and_neighbours = cache(
            self._read_leaf_nr_of_elements_and_neighbours)
        self._read_node_nr_of_elements_and_children_flag = cache(
            self._read_node_nr_of_elements_and_children_flag)

    def _count_props(self):
        """
        Counts dynamic properties for tree, such as all complex formats
        """
        self.single_leaf_record_format = self.key_format + self.meta_format
        self.single_node_record_format = self.pointer_format + \
            self.key_format + self.pointer_format
        self.node_format = self.elements_counter_format + self.flag_format\
            + self.pointer_format + (self.key_format +
                                     self.pointer_format) * self.node_capacity
        self.leaf_format = self.elements_counter_format + self.pointer_format * 2\
            + (self.single_leaf_record_format) * self.node_capacity
        self.leaf_heading_format = self.elements_counter_format + \
            self.pointer_format * 2
        self.node_heading_format = self.elements_counter_format + \
            self.flag_format
        self.key_size = struct.calcsize('<' + self.key_format)
        self.meta_size = struct.calcsize('<' + self.meta_format)
        self.single_leaf_record_size = struct.calcsize('<' + self.
                                                       single_leaf_record_format)
        self.single_node_record_size = struct.calcsize('<' + self.
                                                       single_node_record_format)
        self.node_size = struct.calcsize('<' + self.node_format)
        self.leaf_size = struct.calcsize('<' + self.leaf_format)
        self.flag_size = struct.calcsize('<' + self.flag_format)
        self.elements_counter_size = struct.calcsize('<' + self.
                                                     elements_counter_format)
        self.pointer_size = struct.calcsize('<' + self.pointer_format)
        self.leaf_heading_size = struct.calcsize(
            '<' + self.leaf_heading_format)
        self.node_heading_size = struct.calcsize(
            '<' + self.node_heading_format)

    def create_index(self):
        if os.path.isfile(os.path.join(self.db_path, self.name + '_buck')):
            raise IndexException('Already exists')
        with io.open(os.path.join(self.db_path, self.name + "_buck"), 'w+b') as f:
            props = dict(name=self.name,
                         flag_format=self.flag_format,
                         pointer_format=self.pointer_format,
                         elements_counter_format=self.elements_counter_format,
                         node_capacity=self.node_capacity,
                         key_format=self.key_format,
                         meta_format=self.meta_format,
                         version=self.__version__,
                         storage_class=self.storage_class)
            f.write(marshal.dumps(props))
        self.buckets = io.open(os.path.join(self.db_path, self.name +
                                            "_buck"), 'r+b', buffering=0)
        self._create_storage()
        self.buckets.seek(self._start_ind)
        self.buckets.write(struct.pack('<c', 'l'))
        self._insert_empty_root()
        self.root_flag = 'l'

    def destroy(self):
        super(IU_TreeBasedIndex, self).destroy()
        self._clear_cache()

    def open_index(self):
        if not os.path.isfile(os.path.join(self.db_path, self.name + '_buck')):
            raise IndexException("Doesn't exists")
        self.buckets = io.open(
            os.path.join(self.db_path, self.name + "_buck"), 'r+b', buffering=0)
        self.buckets.seek(self._start_ind)
        self.root_flag = struct.unpack('<c', self.buckets.read(1))[0]
        self._fix_params()
        self._open_storage()

    def _insert_empty_root(self):
        self.buckets.seek(self.data_start)
        root = struct.pack('<' + self.leaf_heading_format,
                           0,
                           0,
                           0)
        root += self.single_leaf_record_size * self.node_capacity * '\x00'
        self.buckets.write(root)
        self.flush()

    def insert(self, doc_id, key, start, size, status='o'):
        nodes_stack, indexes = self._find_leaf_to_insert(key)
        self._insert_new_record_into_leaf(nodes_stack.pop(),
                                          key,
                                          doc_id,
                                          start,
                                          size,
                                          status,
                                          nodes_stack,
                                          indexes)

        self._match_doc_id.delete(doc_id)

    def _read_leaf_nr_of_elements_and_neighbours(self, leaf_start):
        self.buckets.seek(leaf_start)
        data = self.buckets.read(
            self.elements_counter_size + 2 * self.pointer_size)
        nr_of_elements, prev_l, next_l = struct.unpack(
            '<' + self.elements_counter_format + 2 * self.pointer_format,
            data)
        return nr_of_elements, prev_l, next_l

    def _read_node_nr_of_elements_and_children_flag(self, start):
        self.buckets.seek(start)
        data = self.buckets.read(self.elements_counter_size + self.flag_size)
        nr_of_elements, children_flag = struct.unpack(
            '<' + self.elements_counter_format + self.flag_format,
            data)
        return nr_of_elements, children_flag

    def _read_leaf_nr_of_elements(self, start):
        self.buckets.seek(start)
        data = self.buckets.read(self.elements_counter_size)
        nr_of_elements = struct.unpack(
            '<' + self.elements_counter_format, data)
        return nr_of_elements[0]

    def _read_single_node_key(self, node_start, key_index):
        self.buckets.seek(self._calculate_key_position(
            node_start, key_index, 'n'))
        data = self.buckets.read(self.single_node_record_size)
        flag_left, key, pointer_right = struct.unpack(
            '<' + self.single_node_record_format, data)
        return flag_left, key, pointer_right

    def _read_single_leaf_record(self, leaf_start, key_index):
        self.buckets.seek(self._calculate_key_position(
            leaf_start, key_index, 'l'))
        data = self.buckets.read(self.single_leaf_record_size)
        key, doc_id, start, size, status = struct.unpack('<' + self.
                                                         single_leaf_record_format, data)
        return key, doc_id, start, size, status

    def _calculate_key_position(self, start, key_index, flag):
        """
        Calculates position of key in buckets file
        """
        if flag == 'l':
            return start + self.leaf_heading_size + key_index * self.single_leaf_record_size
        elif flag == 'n':
#            returns start position of flag before key[key_index]
            return start + self.node_heading_size + key_index * (self.pointer_size + self.key_size)

    def _match_doc_id(self, doc_id, key, element_index, leaf_start, nr_of_elements):
        curr_key_index = element_index + 1
        curr_leaf_start = leaf_start
        next_leaf = self._read_leaf_neighbours(leaf_start)[1]
        while True:
            if curr_key_index < nr_of_elements:
                curr_key, curr_doc_id, curr_start, curr_size,\
                    curr_status = self._read_single_leaf_record(
                        curr_leaf_start, curr_key_index)
                if key != curr_key:
#                    should't happen, crashes earlier on id index
                    raise DocIdNotFound
                elif doc_id == curr_doc_id and curr_status != 'd':
                    return curr_leaf_start, nr_of_elements, curr_key_index
                else:
                    curr_key_index = curr_key_index + 1
            else:  # there are no more elements in current leaf, must jump to next
                if not next_leaf:  # end of leaf linked list
#                    should't happen, crashes earlier on id index
                    raise DocIdNotFound
                else:
                    curr_leaf_start = next_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(next_leaf)
                    curr_key_index = 0

    def _find_existing(self, key, element_index, leaf_start, nr_of_elements):
        curr_key_index = element_index + 1
        curr_leaf_start = leaf_start
        next_leaf = self._read_leaf_neighbours(leaf_start)[1]
        while True:
            if curr_key_index < nr_of_elements:
                curr_key, curr_doc_id, curr_start, curr_size,\
                    curr_status = self._read_single_leaf_record(
                        curr_leaf_start, curr_key_index)
                if key != curr_key:
                    raise ElemNotFound
                elif curr_status != 'd':
                    return curr_leaf_start, nr_of_elements, curr_key_index
                else:
                    curr_key_index = curr_key_index + 1
            else:  # there are no more elements in current leaf, must jump to next
                if not next_leaf:  # end of leaf linked list
                    raise ElemNotFound
                else:
                    curr_leaf_start = next_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(next_leaf)
                    curr_key_index = 0

    def _update_element(self, leaf_start, key_index, new_data):
        self.buckets.seek(self._calculate_key_position(leaf_start, key_index, 'l')
                          + self.key_size)
        self.buckets.write(struct.pack('<' + self.meta_format,
                                       *new_data))

#        self._read_single_leaf_record.delete(leaf_start_position, key_index)

    def _delete_element(self, leaf_start, key_index):
        self.buckets.seek(self._calculate_key_position(leaf_start, key_index, 'l')
                          + self.single_leaf_record_size - 1)
        self.buckets.write(struct.pack('<c', 'd'))

#        self._read_single_leaf_record.delete(leaf_start_position, key_index)

    def _leaf_linear_key_search(self, key, start, start_index, end_index):
        self.buckets.seek(start)
        data = self.buckets.read(
            (end_index - start_index + 1) * self.single_leaf_record_size)
        curr_key = struct.unpack(
            '<' + self.key_format, data[:self.key_size])[0]
        data = data[self.single_leaf_record_size:]
        curr_index = 0
        while curr_key != key:
            curr_index += 1
            curr_key = struct.unpack(
                '<' + self.key_format, data[:self.key_size])[0]
            data = data[self.single_leaf_record_size:]
        return start_index + curr_index

    def _node_linear_key_search(self, key, start, start_index, end_index):
        self.buckets.seek(start + self.pointer_size)
        data = self.buckets.read((end_index - start_index + 1) * (
            self.key_size + self.pointer_size))
        curr_key = struct.unpack(
            '<' + self.key_format, data[:self.key_size])[0]
        data = data[self.key_size + self.pointer_size:]
        curr_index = 0
        while curr_key != key:
            curr_index += 1
            curr_key = struct.unpack(
                '<' + self.key_format, data[:self.key_size])[0]
            data = data[self.key_size + self.pointer_size:]
        return start_index + curr_index

    def _next_buffer(self, buffer_start, buffer_end):
            return buffer_end, buffer_end + tree_buffer_size

    def _prev_buffer(self, buffer_start, buffer_end):
            return buffer_start - tree_buffer_size, buffer_start

    def _choose_next_candidate_index_in_leaf(self, leaf_start, candidate_start, buffer_start, buffer_end, imin, imax):
        if buffer_start > candidate_start:
            move_buffer = MOVE_BUFFER_PREV
        elif buffer_end < candidate_start + self.single_leaf_record_size:
            move_buffer = MOVE_BUFFER_NEXT
        else:
            move_buffer = None
        return self._calculate_key_position(leaf_start, (imin + imax) / 2, 'l'), (imin + imax) / 2, move_buffer

    def _choose_next_candidate_index_in_node(self, node_start, candidate_start, buffer_start, buffer_end, imin, imax):
        if buffer_start > candidate_start:
            move_buffer = MOVE_BUFFER_PREV
        elif buffer_end < candidate_start + self.single_node_record_size:
            (self.pointer_size + self.key_size) - 1
            move_buffer = MOVE_BUFFER_NEXT
        else:
            move_buffer = None
        return self._calculate_key_position(node_start, (imin + imax) / 2, 'n'), (imin + imax) / 2, move_buffer

    def _find_key_in_leaf(self, leaf_start, key, nr_of_elements):
        if nr_of_elements == 1:
            return self._find_key_in_leaf_with_one_element(key, leaf_start)[-5:]
        else:
            return self._find_key_in_leaf_using_binary_search(key, leaf_start, nr_of_elements)[-5:]

    def _find_key_in_leaf_for_update(self, key, doc_id, leaf_start, nr_of_elements):
        if nr_of_elements == 1:
            return self._find_key_in_leaf_with_one_element(key, leaf_start, doc_id=doc_id)
        else:
            return self._find_key_in_leaf_using_binary_search(key, leaf_start, nr_of_elements, mode=MODE_FIRST, doc_id=doc_id)

    def _find_index_of_first_key_equal_or_smaller_key(self, key, leaf_start, nr_of_elements):
        if nr_of_elements == 1:
            return self._find_key_in_leaf_with_one_element(key, leaf_start, mode=MODE_FIRST, return_closest=True)[:2]
        else:
            return self._find_key_in_leaf_using_binary_search(key, leaf_start, nr_of_elements, mode=MODE_FIRST, return_closest=True)[:2]

    def _find_index_of_last_key_equal_or_smaller_key(self, key, leaf_start, nr_of_elements):
        if nr_of_elements == 1:
            return self._find_key_in_leaf_with_one_element(key, leaf_start, mode=MODE_LAST, return_closest=True)[:2]
        else:
            return self._find_key_in_leaf_using_binary_search(key, leaf_start, nr_of_elements, mode=MODE_LAST, return_closest=True)[:2]

    def _find_index_of_first_key_equal(self, key, leaf_start, nr_of_elements):
        if nr_of_elements == 1:
            return self._find_key_in_leaf_with_one_element(key, leaf_start, mode=MODE_FIRST)[:2]
        else:
            return self._find_key_in_leaf_using_binary_search(key, leaf_start, nr_of_elements, mode=MODE_FIRST)[:2]

    def _find_key_in_leaf_with_one_element(self, key, leaf_start, doc_id=None, mode=None, return_closest=False):
        curr_key, curr_doc_id, curr_start, curr_size,\
            curr_status = self._read_single_leaf_record(leaf_start, 0)
        if key != curr_key:
            if return_closest and curr_status != 'd':
                return leaf_start, 0
            else:
                raise ElemNotFound
        else:
            if curr_status == 'd':
                raise ElemNotFound
            elif doc_id is not None and doc_id != curr_doc_id:
#                    should't happen, crashes earlier on id index
                raise DocIdNotFound
            else:
                return leaf_start, 0, curr_doc_id, curr_key, curr_start, curr_size, curr_status

    def _find_key_in_leaf_using_binary_search(self, key, leaf_start, nr_of_elements, doc_id=None, mode=None, return_closest=False):
        """
        Binary search implementation used in all get functions
        """
        imin, imax = 0, nr_of_elements - 1
        buffer_start, buffer_end = self._set_buffer_limits()
        candidate_start, candidate_index, move_buffer = self._choose_next_candidate_index_in_leaf(leaf_start,
                                                                                                  self._calculate_key_position(leaf_start,
                                                                                                                               (imin + imax) / 2,
                                                                                                                               'l'),
                                                                                                  buffer_start,
                                                                                                  buffer_end,
                                                                                                  imin, imax)
        while imax != imin and imax > imin:
            curr_key, curr_doc_id, curr_start, curr_size, curr_status = self._read_single_leaf_record(leaf_start,
                                                                                                      candidate_index)
            candidate_start = self._calculate_key_position(
                leaf_start, candidate_index, 'l')
            if key < curr_key:
                if move_buffer == MOVE_BUFFER_PREV:
                    buffer_start, buffer_end = self._prev_buffer(
                        buffer_start, buffer_end)
                else:  # if next chosen element is in current buffer, abort moving to other
                    move_buffer is None
                imax = candidate_index - 1
                candidate_start, candidate_index, move_buffer = self._choose_next_candidate_index_in_leaf(leaf_start,
                                                                                                          candidate_start,
                                                                                                          buffer_start,
                                                                                                          buffer_end,
                                                                                                          imin, imax)
            elif key == curr_key:
                if mode == MODE_LAST:
                    if move_buffer == MOVE_BUFFER_NEXT:
                        buffer_start, buffer_end = self._next_buffer(
                            buffer_start, buffer_end)
                    else:
                        move_buffer is None
                    imin = candidate_index + 1
                    candidate_start, candidate_index, move_buffer = self._choose_next_candidate_index_in_leaf(leaf_start,
                                                                                                              candidate_start,
                                                                                                              buffer_start,
                                                                                                              buffer_end,
                                                                                                              imin, imax)
                else:
                    if curr_status == 'o':
                        break
                    else:
                        if move_buffer == MOVE_BUFFER_PREV:
                            buffer_start, buffer_end = self._prev_buffer(
                                buffer_start, buffer_end)
                        else:
                            move_buffer is None
                        imax = candidate_index
                        candidate_start, candidate_index, move_buffer = self._choose_next_candidate_index_in_leaf(leaf_start,
                                                                                                                  candidate_start,
                                                                                                                  buffer_start,
                                                                                                                  buffer_end,
                                                                                                                  imin, imax)
            else:
                if move_buffer == MOVE_BUFFER_NEXT:
                    buffer_start, buffer_end = self._next_buffer(
                        buffer_start, buffer_end)
                else:
                    move_buffer is None
                imin = candidate_index + 1
                candidate_start, candidate_index, move_buffer = self._choose_next_candidate_index_in_leaf(leaf_start,
                                                                                                          candidate_start,
                                                                                                          buffer_start,
                                                                                                          buffer_end,
                                                                                                          imin, imax)

        if imax > imin:
            chosen_key_position = candidate_index
        else:
            chosen_key_position = imax
        curr_key, curr_doc_id, curr_start, curr_size, curr_status = self._read_single_leaf_record(leaf_start,
                                                                                                  chosen_key_position)
        if key != curr_key:
            if return_closest:  # useful for find all bigger/smaller methods
                return leaf_start, chosen_key_position
            else:
                raise ElemNotFound
        if doc_id and doc_id == curr_doc_id and curr_status == 'o':
            return leaf_start, chosen_key_position, curr_doc_id, curr_key, curr_start, curr_size, curr_status
        else:
            if mode == MODE_FIRST and imin < chosen_key_position:  # check if there isn't any element with equal key before chosen one
                matching_record_index = self._leaf_linear_key_search(key,
                                                                     self._calculate_key_position(leaf_start,
                                                                                                  imin,
                                                                                                  'l'),
                                                                     imin,
                                                                     chosen_key_position)
            else:
                matching_record_index = chosen_key_position
            curr_key, curr_doc_id, curr_start, curr_size, curr_status = self._read_single_leaf_record(leaf_start,
                                                                                                      matching_record_index)
            if curr_status == 'd' and not return_closest:
                leaf_start, nr_of_elements, matching_record_index = self._find_existing(key,
                                                                                        matching_record_index,
                                                                                        leaf_start,
                                                                                        nr_of_elements)
                curr_key, curr_doc_id, curr_start, curr_size, curr_status = self._read_single_leaf_record(leaf_start,
                                                                                                          matching_record_index)
            if doc_id is not None and doc_id != curr_doc_id:
                leaf_start, nr_of_elements, matching_record_index = self._match_doc_id(doc_id,
                                                                                       key,
                                                                                       matching_record_index,
                                                                                       leaf_start,
                                                                                       nr_of_elements)
                curr_key, curr_doc_id, curr_start, curr_size, curr_status = self._read_single_leaf_record(leaf_start,
                                                                                                          matching_record_index)
            return leaf_start, matching_record_index, curr_doc_id, curr_key, curr_start, curr_size, curr_status

    def _find_place_in_leaf(self, key, leaf_start, nr_of_elements):
        if nr_of_elements == 1:
            return self._find_place_in_leaf_with_one_element(key, leaf_start)
        else:
            return self._find_place_in_leaf_using_binary_search(key, leaf_start, nr_of_elements)

    def _find_place_in_leaf_with_one_element(self, key, leaf_start):
        curr_key, curr_doc_id, curr_start, curr_size,\
            curr_status = self._read_single_leaf_record(leaf_start, 0)
        if curr_status == 'd':
                return leaf_start, 0, 0, False, True  # leaf start, index of new key position, nr of rec to rewrite, full_leaf flag, on_deleted flag
        else:
            if key < curr_key:
                return leaf_start, 0, 1, False, False
            else:
                return leaf_start, 1, 0, False, False

    def _find_place_in_leaf_using_binary_search(self, key, leaf_start, nr_of_elements):
        """
        Binary search implementation used in insert function
        """
        imin, imax = 0, nr_of_elements - 1
        buffer_start, buffer_end = self._set_buffer_limits()
        candidate_start, candidate_index, move_buffer = self._choose_next_candidate_index_in_leaf(leaf_start,
                                                                                                  self._calculate_key_position(leaf_start,
                                                                                                                               (imin + imax) / 2,
                                                                                                                               'l'),
                                                                                                  buffer_start,
                                                                                                  buffer_end,
                                                                                                  imin, imax)
        while imax != imin and imax > imin:
            curr_key, curr_doc_id, curr_start, curr_size, curr_status = self._read_single_leaf_record(leaf_start,
                                                                                                      candidate_index)
            candidate_start = self._calculate_key_position(
                leaf_start, candidate_index, 'l')
            if key < curr_key:
                if move_buffer == MOVE_BUFFER_PREV:
                    buffer_start, buffer_end = self._prev_buffer(
                        buffer_start, buffer_end)
                else:  # if next chosen element is in current buffer, abort moving to other
                    move_buffer is None
                imax = candidate_index - 1
                candidate_start, candidate_index, move_buffer = self._choose_next_candidate_index_in_leaf(leaf_start,
                                                                                                          candidate_start,
                                                                                                          buffer_start,
                                                                                                          buffer_end,
                                                                                                          imin, imax)
            else:
                if move_buffer == MOVE_BUFFER_NEXT:
                    buffer_start, buffer_end = self._next_buffer(
                        buffer_start, buffer_end)
                else:
                    move_buffer is None
                imin = candidate_index + 1
                candidate_start, candidate_index, move_buffer = self._choose_next_candidate_index_in_leaf(leaf_start,
                                                                                                          candidate_start,
                                                                                                          buffer_start,
                                                                                                          buffer_end,
                                                                                                          imin, imax)
        if imax < imin and imin < nr_of_elements:
            chosen_key_position = imin
        else:
            chosen_key_position = imax
        curr_key, curr_doc_id, curr_start, curr_size, curr_status = self._read_single_leaf_record(leaf_start,
                                                                                                  chosen_key_position)
        if curr_status == 'd':
            return leaf_start, chosen_key_position, 0, False, True
        elif key < curr_key:
            if chosen_key_position > 0:
                curr_key, curr_doc_id, curr_start, curr_size, curr_status = self._read_single_leaf_record(leaf_start,
                                                                                                          chosen_key_position - 1)
                if curr_start == 'd':
                    return leaf_start, chosen_key_position - 1, 0, False, True
                else:
                    return leaf_start, chosen_key_position, nr_of_elements - chosen_key_position, (nr_of_elements == self.node_capacity), False
            else:
                return leaf_start, chosen_key_position, nr_of_elements - chosen_key_position, (nr_of_elements == self.node_capacity), False
        else:
            if chosen_key_position < nr_of_elements - 1:
                curr_key, curr_doc_id, curr_start, curr_size, curr_status = self._read_single_leaf_record(leaf_start,
                                                                                                          chosen_key_position + 1)
                if curr_start == 'd':
                    return leaf_start, chosen_key_position + 1, 0, False, True
                else:
                    return leaf_start, chosen_key_position + 1, nr_of_elements - chosen_key_position - 1, (nr_of_elements == self.node_capacity), False
            else:
                return leaf_start, chosen_key_position + 1, nr_of_elements - chosen_key_position - 1, (nr_of_elements == self.node_capacity), False

    def _set_buffer_limits(self):
        pos = self.buckets.tell()
        buffer_start = pos - (pos % tree_buffer_size)
        return buffer_start, (buffer_start + tree_buffer_size)

    def _find_first_key_occurence_in_node(self, node_start, key, nr_of_elements):
        if nr_of_elements == 1:
            return self._find_key_in_node_with_one_element(key, node_start, mode=MODE_FIRST)
        else:
            return self._find_key_in_node_using_binary_search(key, node_start, nr_of_elements, mode=MODE_FIRST)

    def _find_last_key_occurence_in_node(self, node_start, key, nr_of_elements):
        if nr_of_elements == 1:
            return self._find_key_in_node_with_one_element(key, node_start, mode=MODE_LAST)
        else:
            return self._find_key_in_node_using_binary_search(key, node_start, nr_of_elements, mode=MODE_LAST)

    def _find_key_in_node_with_one_element(self, key, node_start, mode=None):
        l_pointer, curr_key, r_pointer = self._read_single_node_key(
            node_start, 0)
        if key < curr_key:
            return 0, l_pointer
        elif key > curr_key:
            return 0, r_pointer
        else:
            if mode == MODE_FIRST:
                return 0, l_pointer
            elif mode == MODE_LAST:
                return 0, r_pointer
            else:
                raise Exception('Invalid mode declared: set first/last')

    def _find_key_in_node_using_binary_search(self, key, node_start, nr_of_elements, mode=None):
        imin, imax = 0, nr_of_elements - 1
        buffer_start, buffer_end = self._set_buffer_limits()
        candidate_start, candidate_index, move_buffer = self._choose_next_candidate_index_in_node(node_start,
                                                                                                  self._calculate_key_position(node_start,
                                                                                                                               (imin + imax) / 2,
                                                                                                                               'n'),
                                                                                                  buffer_start,
                                                                                                  buffer_end,
                                                                                                  imin, imax)
        while imax != imin and imax > imin:
            l_pointer, curr_key, r_pointer = self._read_single_node_key(
                node_start, candidate_index)
            candidate_start = self._calculate_key_position(
                node_start, candidate_index, 'n')
            if key < curr_key:
                if move_buffer == MOVE_BUFFER_PREV:
                    buffer_start, buffer_end = self._prev_buffer(
                        buffer_start, buffer_end)
                else:  # if next chosen element is in current buffer, abort moving to other
                    move_buffer is None
                imax = candidate_index - 1
                candidate_start, candidate_index, move_buffer = self._choose_next_candidate_index_in_node(node_start,
                                                                                                          candidate_start,
                                                                                                          buffer_start,
                                                                                                          buffer_end,
                                                                                                          imin, imax)
            elif key == curr_key:
                if mode == MODE_LAST:
                    if move_buffer == MOVE_BUFFER_NEXT:
                        buffer_start, buffer_end = self._next_buffer(
                            buffer_start, buffer_end)
                    else:
                        move_buffer is None
                    imin = candidate_index + 1
                    candidate_start, candidate_index, move_buffer = self._choose_next_candidate_index_in_node(node_start,
                                                                                                              candidate_start,
                                                                                                              buffer_start,
                                                                                                              buffer_end,
                                                                                                              imin, imax)
                else:
                    break
            else:
                if move_buffer == MOVE_BUFFER_NEXT:
                        buffer_start, buffer_end = self._next_buffer(
                            buffer_start, buffer_end)
                else:
                    move_buffer is None
                imin = candidate_index + 1
                candidate_start, candidate_index, move_buffer = self._choose_next_candidate_index_in_node(node_start,
                                                                                                          candidate_start,
                                                                                                          buffer_start,
                                                                                                          buffer_end,
                                                                                                          imin, imax)

        if imax > imin:
            chosen_key_position = candidate_index
        elif imax < imin and imin < nr_of_elements:
            chosen_key_position = imin
        else:
            chosen_key_position = imax
        l_pointer, curr_key, r_pointer = self._read_single_node_key(
            node_start, chosen_key_position)
        if mode == MODE_FIRST and imin < chosen_key_position:  # check if there is no elements with equal key before chosen one
            matching_record_index = self._node_linear_key_search(key,
                                                                 self._calculate_key_position(node_start,
                                                                                              imin,
                                                                                              'n'),
                                                                 imin,
                                                                 chosen_key_position)
        else:
            matching_record_index = chosen_key_position
        l_pointer, curr_key, r_pointer = self._read_single_node_key(
            node_start, matching_record_index)
        if key < curr_key:
            return matching_record_index, l_pointer
        elif key > curr_key:
            return matching_record_index, r_pointer
        else:
            if mode == MODE_FIRST:
                return matching_record_index, l_pointer
            elif mode == MODE_LAST:
                return matching_record_index, r_pointer
            else:
                raise Exception('Invalid mode declared: first/last')

    def _update_leaf_ready_data(self, leaf_start, start_index, new_nr_of_elements, records_to_rewrite):
        self.buckets.seek(leaf_start)
        self.buckets.write(struct.pack('<h', new_nr_of_elements))
        start_position = self._calculate_key_position(
            leaf_start, start_index, 'l')
        self.buckets.seek(start_position)
        self.buckets.write(
            struct.pack(
                '<' + (new_nr_of_elements - start_index) *
                self.single_leaf_record_format,
                *records_to_rewrite))

#        self._read_single_leaf_record.delete(leaf_start)
        self._read_leaf_nr_of_elements.delete(leaf_start)
        self._read_leaf_nr_of_elements_and_neighbours.delete(leaf_start)

    def _update_leaf(self, leaf_start, new_record_position, nr_of_elements,
                     nr_of_records_to_rewrite, on_deleted, new_key,
                     new_doc_id, new_start, new_size, new_status):
        if nr_of_records_to_rewrite == 0:  # just write at set position
            self.buckets.seek(self._calculate_key_position(
                leaf_start, new_record_position, 'l'))
            self.buckets.write(
                struct.pack('<' + self.single_leaf_record_format,
                            new_key,
                            new_doc_id,
                            new_start,
                            new_size,
                            new_status))
            self.flush()
        else:  # must read all elems after new one, and rewrite them after new
            start = self._calculate_key_position(
                leaf_start, new_record_position, 'l')
            self.buckets.seek(start)
            data = self.buckets.read(nr_of_records_to_rewrite *
                                     self.single_leaf_record_size)
            records_to_rewrite = struct.unpack('<' + nr_of_records_to_rewrite *
                                               self.single_leaf_record_format, data)
            curr_index = 0
            records_to_rewrite = list(records_to_rewrite)
            for status in records_to_rewrite[4::5]:  # don't write back deleted records, deleting them from list
                if status != 'o':
                    del records_to_rewrite[curr_index * 5:curr_index * 5 + 5]
                    nr_of_records_to_rewrite -= 1
                    nr_of_elements -= 1
                else:
                    curr_index += 1

            self.buckets.seek(start)
            self.buckets.write(
                struct.pack(
                    '<' + (nr_of_records_to_rewrite +
                           1) * self.single_leaf_record_format,
                    new_key,
                    new_doc_id,
                    new_start,
                    new_size,
                    new_status,
                    *tuple(records_to_rewrite)))
            self.flush()
        self.buckets.seek(leaf_start)
        if not on_deleted:  # when new record replaced deleted one, nr of leaf elements stays the same
            self.buckets.write(struct.pack('<h', nr_of_elements + 1))

        self._read_leaf_nr_of_elements.delete(leaf_start)
        self._read_leaf_nr_of_elements_and_neighbours.delete(leaf_start)
        self._find_key_in_leaf.delete(leaf_start)
#        self._read_single_leaf_record.delete(leaf_start)

    def _read_leaf_neighbours(self, leaf_start):
        self.buckets.seek(leaf_start + self.elements_counter_size)
        neihbours_data = self.buckets.read(2 * self.pointer_size)
        prev_l, next_l = struct.unpack(
            '<' + 2 * self.pointer_format, neihbours_data)
        return prev_l, next_l

    def _update_leaf_size_and_pointers(self, leaf_start, new_size, new_prev, new_next):
        self.buckets.seek(leaf_start)
        self.buckets.write(
            struct.pack(
                '<' + self.elements_counter_format + 2 * self.pointer_format,
                new_size,
                new_prev,
                new_next))

        self._read_leaf_nr_of_elements.delete(leaf_start)
        self._read_leaf_neighbours.delete(leaf_start)
        self._read_leaf_nr_of_elements_and_neighbours.delete(leaf_start)

    def _update_leaf_prev_pointer(self, leaf_start, pointer):
        self.buckets.seek(leaf_start + self.elements_counter_size)
        self.buckets.write(struct.pack('<' + self.pointer_format,
                                       pointer))

        self._read_leaf_neighbours.delete(leaf_start)
        self._read_leaf_nr_of_elements_and_neighbours.delete(leaf_start)

    def _update_size(self, start, new_size):
        self.buckets.seek(start)
        self.buckets.write(struct.pack('<' + self.elements_counter_format,
                                       new_size))

        self._read_leaf_nr_of_elements.delete(start)
        self._read_leaf_nr_of_elements_and_neighbours.delete(start)

    def _create_new_root_from_leaf(self, leaf_start, nr_of_records_to_rewrite, new_leaf_size, old_leaf_size, half_size, new_data):
        blanks = (self.node_capacity - new_leaf_size) * \
            self.single_leaf_record_size * '\x00'
        left_leaf_start_position = self.data_start + self.node_size
        right_leaf_start_position = self.data_start + \
            self.node_size + self.leaf_size
        self.buckets.seek(self.data_start + self.leaf_heading_size)
        # read old root
        data = self.buckets.read(
            self.single_leaf_record_size * self.node_capacity)
        leaf_data = struct.unpack('<' + self.
                                  single_leaf_record_format * self.node_capacity, data)
        # remove deleted records, if succeded abort spliting
        if self._update_if_has_deleted(self.data_start, leaf_data, 0, new_data):
            return None
        # find out key which goes to parent node
        if nr_of_records_to_rewrite > new_leaf_size - 1:
            key_moved_to_parent_node = leaf_data[(old_leaf_size - 1) * 5]
        elif nr_of_records_to_rewrite == new_leaf_size - 1:
            key_moved_to_parent_node = new_data[0]
        else:
            key_moved_to_parent_node = leaf_data[old_leaf_size * 5]
        data_to_write = self._prepare_new_root_data(key_moved_to_parent_node,
                                                    left_leaf_start_position,
                                                    right_leaf_start_position,
                                                    'l')
        if nr_of_records_to_rewrite > half_size:
                # key goes to first half
                # prepare left leaf data
            left_leaf_data = struct.pack('<' + self.leaf_heading_format + self.single_leaf_record_format
                                         * (self.node_capacity - nr_of_records_to_rewrite),
                                         old_leaf_size,
                                         0,
                                         right_leaf_start_position,
                                         *leaf_data[:-nr_of_records_to_rewrite * 5])
            left_leaf_data += struct.pack(
                '<' + self.single_leaf_record_format * (
                    nr_of_records_to_rewrite - new_leaf_size + 1),
                new_data[0],
                new_data[1],
                new_data[2],
                new_data[3],
                new_data[4],
                *leaf_data[-nr_of_records_to_rewrite * 5:(old_leaf_size - 1) * 5])
                # prepare right leaf_data
            right_leaf_data = struct.pack('<' + self.elements_counter_format + 2 * self.pointer_format +
                                          self.single_leaf_record_format *
                                          new_leaf_size,
                                          new_leaf_size,
                                          left_leaf_start_position,
                                          0,
                                          *leaf_data[-new_leaf_size * 5:])
        else:
                # key goes to second half
            if nr_of_records_to_rewrite:
                records_before = leaf_data[old_leaf_size *
                                           5:-nr_of_records_to_rewrite * 5]
                records_after = leaf_data[-nr_of_records_to_rewrite * 5:]
            else:
                records_before = leaf_data[old_leaf_size * 5:]
                records_after = []

            left_leaf_data = struct.pack(
                '<' + self.leaf_heading_format +
                self.single_leaf_record_format * old_leaf_size,
                old_leaf_size,
                0,
                right_leaf_start_position,
                *leaf_data[:old_leaf_size * 5])
                # prepare right leaf_data
            right_leaf_data = struct.pack('<' + self.elements_counter_format + 2 * self.pointer_format +
                                          self.single_leaf_record_format * (new_leaf_size -
                                                                            nr_of_records_to_rewrite - 1),
                                          new_leaf_size,
                                          left_leaf_start_position,
                                          0,
                                          *records_before)
            right_leaf_data += struct.pack(
                '<' + self.single_leaf_record_format * (
                    nr_of_records_to_rewrite + 1),
                new_data[0],
                new_data[1],
                new_data[2],
                new_data[3],
                new_data[4],
                *records_after)
        left_leaf_data += (self.node_capacity -
                           old_leaf_size) * self.single_leaf_record_size * '\x00'
        right_leaf_data += blanks
        data_to_write += left_leaf_data
        data_to_write += right_leaf_data
        self.buckets.seek(self._start_ind)
        self.buckets.write(struct.pack('<c', 'n') + data_to_write)
        self.root_flag = 'n'

#            self._read_single_leaf_record.delete(leaf_start)
        self._find_key_in_leaf.delete(leaf_start)
        self._read_leaf_nr_of_elements.delete(leaf_start)
        self._read_leaf_nr_of_elements_and_neighbours.delete(leaf_start)
        self._read_leaf_neighbours.delete(leaf_start)
        return None

    def _split_leaf(
        self, leaf_start, nr_of_records_to_rewrite, new_key, new_doc_id, new_start, new_size, new_status,
            create_new_root=False):
        """
        Splits full leaf in two separate ones, first half of records stays on old position,
        second half is written as new leaf at the end of file.
        """
        half_size = self.node_capacity / 2
        if self.node_capacity % 2 == 0:
            old_leaf_size = half_size
            new_leaf_size = half_size + 1
        else:
            old_leaf_size = new_leaf_size = half_size + 1
        if create_new_root:  # leaf is a root
            new_data = [new_key, new_doc_id, new_start, new_size, new_status]
            self._create_new_root_from_leaf(leaf_start, nr_of_records_to_rewrite, new_leaf_size, old_leaf_size, half_size, new_data)
        else:
            blanks = (self.node_capacity - new_leaf_size) * \
                self.single_leaf_record_size * '\x00'
            prev_l, next_l = self._read_leaf_neighbours(leaf_start)
            if nr_of_records_to_rewrite > half_size:  # insert key into first half of leaf
                self.buckets.seek(self._calculate_key_position(leaf_start,
                                                               self.node_capacity - nr_of_records_to_rewrite,
                                                               'l'))
                # read all records with key>new_key
                data = self.buckets.read(
                    nr_of_records_to_rewrite * self.single_leaf_record_size)
                records_to_rewrite = struct.unpack(
                    '<' + nr_of_records_to_rewrite * self.single_leaf_record_format, data)
                # remove deleted records, if succeded abort spliting
                if self._update_if_has_deleted(leaf_start,
                                               records_to_rewrite,
                                               self.node_capacity -
                                               nr_of_records_to_rewrite,
                                               [new_key, new_doc_id, new_start, new_size, new_status]):
                    return None
                key_moved_to_parent_node = records_to_rewrite[
                    -new_leaf_size * 5]
                # write new leaf at end of file
                self.buckets.seek(0, 2)  # end of file
                new_leaf_start = self.buckets.tell()
                # prepare new leaf_data
                new_leaf = struct.pack('<' + self.elements_counter_format + 2 * self.pointer_format +
                                       self.single_leaf_record_format *
                                       new_leaf_size,
                                       new_leaf_size,
                                       leaf_start,
                                       next_l,
                                       *records_to_rewrite[-new_leaf_size * 5:])
                new_leaf += blanks
                # write new leaf
                self.buckets.write(new_leaf)
                # update old leaf heading
                self._update_leaf_size_and_pointers(leaf_start,
                                                    old_leaf_size,
                                                    prev_l,
                                                    new_leaf_start)
                # seek position of new key in first half
                self.buckets.seek(self._calculate_key_position(leaf_start,
                                                               self.node_capacity - nr_of_records_to_rewrite,
                                                               'l'))
                # write new key and keys after
                self.buckets.write(
                    struct.pack(
                        '<' + self.single_leaf_record_format *
                        (nr_of_records_to_rewrite - new_leaf_size + 1),
                        new_key,
                        new_doc_id,
                        new_start,
                        new_size,
                        'o',
                        *records_to_rewrite[:-new_leaf_size * 5]))

                if next_l:  # when next_l is 0 there is no next leaf to update, avoids writing data at 0 position of file
                    self._update_leaf_prev_pointer(
                        next_l, new_leaf_start)

#                self._read_single_leaf_record.delete(leaf_start)
                self._find_key_in_leaf.delete(leaf_start)

                return new_leaf_start, key_moved_to_parent_node
            else:  # key goes into second half of leaf     '
                # seek half of the leaf
                self.buckets.seek(self._calculate_key_position(
                    leaf_start, old_leaf_size, 'l'))
                data = self.buckets.read(
                    self.single_leaf_record_size * (new_leaf_size - 1))
                records_to_rewrite = struct.unpack('<' + (new_leaf_size - 1) *
                                                   self.single_leaf_record_format, data)
                # remove deleted records, if succeded abort spliting
                if self._update_if_has_deleted(leaf_start,
                                               records_to_rewrite,
                                               old_leaf_size,
                                               [new_key, new_doc_id, new_start, new_size, new_status]):
                    return None
                key_moved_to_parent_node = records_to_rewrite[
                    -(new_leaf_size - 1) * 5]
                if key_moved_to_parent_node > new_key:
                    key_moved_to_parent_node = new_key
                self.buckets.seek(0, 2)  # end of file
                new_leaf_start = self.buckets.tell()
                # prepare new leaf data
                index_of_records_split = nr_of_records_to_rewrite * 5
                if index_of_records_split:
                    records_before = records_to_rewrite[
                        :-index_of_records_split]
                    records_after = records_to_rewrite[
                        -index_of_records_split:]
                else:
                    records_before = records_to_rewrite
                    records_after = []
                new_leaf = struct.pack('<' + self.elements_counter_format + 2 * self.pointer_format
                                       + self.single_leaf_record_format * (new_leaf_size -
                                                                           nr_of_records_to_rewrite - 1),
                                       new_leaf_size,
                                       leaf_start,
                                       next_l,
                                       *records_before)
                new_leaf += struct.pack(
                    '<' + self.single_leaf_record_format *
                    (nr_of_records_to_rewrite + 1),
                    new_key,
                    new_doc_id,
                    new_start,
                    new_size,
                    'o',
                    *records_after)
                new_leaf += blanks
                self.buckets.write(new_leaf)
                self._update_leaf_size_and_pointers(leaf_start,
                                                    old_leaf_size,
                                                    prev_l,
                                                    new_leaf_start)
                if next_l:  # pren next_l is 0 there is no next leaf to update, avoids writing data at 0 position of file
                    self._update_leaf_prev_pointer(
                        next_l, new_leaf_start)

#                self._read_single_leaf_record.delete(leaf_start)
                self._find_key_in_leaf.delete(leaf_start)

                return new_leaf_start, key_moved_to_parent_node

    def _update_if_has_deleted(self, leaf_start, records_to_rewrite, start_position, new_record_data):
        """
        Checks if there are any deleted elements in data to rewrite and prevent from writing then back.
        """
        curr_index = 0
        nr_of_elements = self.node_capacity
        records_to_rewrite = list(records_to_rewrite)
        for status in records_to_rewrite[4::5]:  # remove deleted from list
            if status != 'o':
                del records_to_rewrite[curr_index * 5:curr_index * 5 + 5]
                nr_of_elements -= 1
            else:
                curr_index += 1
        # if were deleted dont have to split, just update leaf
        if nr_of_elements < self.node_capacity:
            data_split_index = 0
            for key in records_to_rewrite[0::5]:
                if key > new_record_data[0]:
                    break
                else:
                    data_split_index += 1
            records_to_rewrite = records_to_rewrite[:data_split_index * 5]\
                + new_record_data\
                + records_to_rewrite[data_split_index * 5:]
            self._update_leaf_ready_data(leaf_start,
                                         start_position,
                                         nr_of_elements + 1,
                                         records_to_rewrite),
            return True
        else:  # did not found any deleted records in leaf
            return False

    def _prepare_new_root_data(self, root_key, left_pointer, right_pointer, children_flag='n'):
        new_root = struct.pack(
            '<' + self.node_heading_format + self.single_node_record_format,
            1,
            children_flag,
            left_pointer,
            root_key,
            right_pointer)
        new_root += (self.key_size + self.pointer_size) * (self.
                                                           node_capacity - 1) * '\x00'
        return new_root

    def _create_new_root_from_node(self, node_start, children_flag, nr_of_keys_to_rewrite, new_node_size, old_node_size, new_key, new_pointer):
            # reading second half of node
            self.buckets.seek(self.data_start + self.node_heading_size)
            # read all keys with key>new_key
            data = self.buckets.read(self.pointer_size + self.
                                     node_capacity * (self.key_size + self.pointer_size))
            old_node_data = struct.unpack('<' + self.pointer_format + self.node_capacity *
                                          (self.key_format + self.pointer_format), data)
            self.buckets.seek(0, 2)  # end of file
            new_node_start = self.buckets.tell()
            if nr_of_keys_to_rewrite == new_node_size:
                key_moved_to_root = new_key
                # prepare new nodes data
                left_node = struct.pack('<' + self.node_heading_format + self.pointer_format +
                                        old_node_size * (self.
                                                         key_format + self.pointer_format),
                                        old_node_size,
                                        children_flag,
                                        *old_node_data[:old_node_size * 2 + 1])

                right_node = struct.pack('<' + self.node_heading_format + self.pointer_format +
                                         new_node_size * (self.
                                                          key_format + self.pointer_format),
                                         new_node_size,
                                         children_flag,
                                         new_pointer,
                                         *old_node_data[old_node_size * 2 + 1:])
            elif nr_of_keys_to_rewrite > new_node_size:
                key_moved_to_root = old_node_data[old_node_size * 2 - 1]
                # prepare new nodes data
                if nr_of_keys_to_rewrite == self.node_capacity:
                    keys_before = old_node_data[:1]
                    keys_after = old_node_data[1:old_node_size * 2 - 1]
                else:
                    keys_before = old_node_data[:-nr_of_keys_to_rewrite * 2]
                    keys_after = old_node_data[-(
                        nr_of_keys_to_rewrite) * 2:old_node_size * 2 - 1]
                left_node = struct.pack('<' + self.node_heading_format + self.pointer_format +
                                        (self.node_capacity - nr_of_keys_to_rewrite) * (self.
                                                                                        key_format + self.pointer_format),
                                        old_node_size,
                                        children_flag,
                                        *keys_before)
                left_node += struct.pack(
                    '<' + (self.key_format + self.pointer_format) *
                    (nr_of_keys_to_rewrite - new_node_size),
                    new_key,
                    new_pointer,
                    *keys_after)

                right_node = struct.pack('<' + self.node_heading_format + self.pointer_format +
                                         new_node_size * (self.
                                                          key_format + self.pointer_format),
                                         new_node_size,
                                         children_flag,
                                         *old_node_data[old_node_size * 2:])
            else:
#               'inserting key into second half of node and creating new root'
                key_moved_to_root = old_node_data[old_node_size * 2 + 1]
                # prepare new nodes data
                left_node = struct.pack('<' + self.node_heading_format + self.pointer_format +
                                        old_node_size * (self.
                                                         key_format + self.pointer_format),
                                        old_node_size,
                                        children_flag,
                                        *old_node_data[:old_node_size * 2 + 1])
                if nr_of_keys_to_rewrite:
                    keys_before = old_node_data[(old_node_size +
                                                 1) * 2:-nr_of_keys_to_rewrite * 2]
                    keys_after = old_node_data[-nr_of_keys_to_rewrite * 2:]
                else:
                    keys_before = old_node_data[(old_node_size + 1) * 2:]
                    keys_after = []
                right_node = struct.pack('<' + self.node_heading_format + self.pointer_format +
                                         (new_node_size - nr_of_keys_to_rewrite - 1) * (self.
                                                                                        key_format + self.pointer_format),
                                         new_node_size,
                                         children_flag,
                                         *keys_before)
                right_node += struct.pack(
                    '<' + (nr_of_keys_to_rewrite + 1) *
                    (self.key_format + self.pointer_format),
                    new_key,
                    new_pointer,
                    *keys_after)
            new_root = self._prepare_new_root_data(key_moved_to_root,
                                                   new_node_start,
                                                   new_node_start + self.node_size)
            left_node += (self.node_capacity - old_node_size) * \
                (self.key_size + self.pointer_size) * '\x00'
            # adding blanks after new node
            right_node += (self.node_capacity - new_node_size) * \
                (self.key_size + self.pointer_size) * '\x00'
            self.buckets.seek(0, 2)
            self.buckets.write(left_node + right_node)
            self.buckets.seek(self.data_start)
            self.buckets.write(new_root)

            self._read_single_node_key.delete(node_start)
            self._read_node_nr_of_elements_and_children_flag.delete(node_start)
            return None

    def _split_node(self, node_start, nr_of_keys_to_rewrite, new_key, new_pointer, children_flag, create_new_root=False):
        """
        Splits full node in two separate ones, first half of records stays on old position,
        second half is written as new leaf at the end of file.
        """
        half_size = self.node_capacity / 2
        if self.node_capacity % 2 == 0:
            old_node_size = new_node_size = half_size
        else:
            old_node_size = half_size
            new_node_size = half_size + 1
        if create_new_root:
            self._create_new_root_from_node(node_start, children_flag, nr_of_keys_to_rewrite, new_node_size, old_node_size, new_key, new_pointer)
        else:
            blanks = (self.node_capacity - new_node_size) * (
                self.key_size + self.pointer_size) * '\x00'
            if nr_of_keys_to_rewrite == new_node_size:  # insert key into first half of node
                # reading second half of node
                self.buckets.seek(self._calculate_key_position(node_start,
                                                               old_node_size,
                                                               'n') + self.pointer_size)
                # read all keys with key>new_key
                data = self.buckets.read(nr_of_keys_to_rewrite *
                                         (self.key_size + self.pointer_size))
                old_node_data = struct.unpack('<' + nr_of_keys_to_rewrite *
                                              (self.key_format + self.pointer_format), data)
                # write new node at end of file
                self.buckets.seek(0, 2)
                new_node_start = self.buckets.tell()
                # prepare new node_data
                new_node = struct.pack('<' + self.node_heading_format + self.pointer_format +
                                       (self.key_format +
                                        self.pointer_format) * new_node_size,
                                       new_node_size,
                                       children_flag,
                                       new_pointer,
                                       *old_node_data)
                new_node += blanks
                # write new node
                self.buckets.write(new_node)
                # update old node data
                self._update_size(
                    node_start, old_node_size)

                self._read_single_node_key.delete(node_start)
                self._read_node_nr_of_elements_and_children_flag.delete(
                    node_start)

                return new_node_start, new_key
            elif nr_of_keys_to_rewrite > half_size:  # insert key into first half of node
                # seek for first key to rewrite
                self.buckets.seek(self._calculate_key_position(node_start, self.node_capacity - nr_of_keys_to_rewrite, 'n')
                                  + self.pointer_size)
                # read all keys with key>new_key
                data = self.buckets.read(
                    nr_of_keys_to_rewrite * (self.key_size + self.pointer_size))
                old_node_data = struct.unpack(
                    '<' + nr_of_keys_to_rewrite * (self.key_format + self.pointer_format), data)
                key_moved_to_parent_node = old_node_data[-(
                    new_node_size + 1) * 2]
                self.buckets.seek(0, 2)
                new_node_start = self.buckets.tell()
                # prepare new node_data
                new_node = struct.pack('<' + self.node_heading_format +
                                       self.pointer_format + (self.key_format +
                                                              self.pointer_format) * new_node_size,
                                       new_node_size,
                                       children_flag,
                                       old_node_data[-new_node_size * 2 - 1],
                                       *old_node_data[-new_node_size * 2:])
                new_node += blanks
                # write new node
                self.buckets.write(new_node)
                self._update_size(
                    node_start, old_node_size)
                # seek position of new key in first half
                self.buckets.seek(self._calculate_key_position(node_start, self.node_capacity - nr_of_keys_to_rewrite, 'n')
                                  + self.pointer_size)
                # write new key and keys after
                self.buckets.write(
                    struct.pack(
                        '<' + (self.key_format + self.pointer_format) *
                        (nr_of_keys_to_rewrite - new_node_size),
                        new_key,
                        new_pointer,
                        *old_node_data[:-(new_node_size + 1) * 2]))

                self._read_single_node_key.delete(node_start)
                self._read_node_nr_of_elements_and_children_flag.delete(
                    node_start)

                return new_node_start, key_moved_to_parent_node
            else:  # key goes into second half
                # reading second half of node
                self.buckets.seek(self._calculate_key_position(node_start,
                                                               old_node_size,
                                                               'n')
                                  + self.pointer_size)
                data = self.buckets.read(
                    new_node_size * (self.key_size + self.pointer_size))
                old_node_data = struct.unpack('<' + new_node_size *
                                              (self.key_format + self.pointer_format), data)
                # find key which goes to parent node
                key_moved_to_parent_node = old_node_data[0]
                self.buckets.seek(0, 2)  # end of file
                new_node_start = self.buckets.tell()
                index_of_records_split = nr_of_keys_to_rewrite * 2
                # prepare new node_data
                first_leaf_pointer = old_node_data[1]
                old_node_data = old_node_data[2:]
                if index_of_records_split:
                    keys_before = old_node_data[:-index_of_records_split]
                    keys_after = old_node_data[-index_of_records_split:]
                else:
                    keys_before = old_node_data
                    keys_after = []
                new_node = struct.pack('<' + self.node_heading_format + self.pointer_format +
                                       (self.key_format + self.pointer_format) *
                                       (new_node_size -
                                        nr_of_keys_to_rewrite - 1),
                                       new_node_size,
                                       children_flag,
                                       first_leaf_pointer,
                                       *keys_before)
                new_node += struct.pack('<' + (self.key_format + self.pointer_format) *
                                        (nr_of_keys_to_rewrite + 1),
                                        new_key,
                                        new_pointer,
                                        *keys_after)
                new_node += blanks
                # write new node
                self.buckets.write(new_node)
                self._update_size(node_start, old_node_size)

                self._read_single_node_key.delete(node_start)
                self._read_node_nr_of_elements_and_children_flag.delete(
                    node_start)

                return new_node_start, key_moved_to_parent_node

    def insert_first_record_into_leaf(self, leaf_start, key, doc_id, start, size, status):
        self.buckets.seek(leaf_start)
        self.buckets.write(struct.pack('<' + self.elements_counter_format,
                                       1))
        self.buckets.seek(leaf_start + self.leaf_heading_size)
        self.buckets.write(struct.pack('<' + self.single_leaf_record_format,
                                       key,
                                       doc_id,
                                       start,
                                       size,
                                       status))

#            self._read_single_leaf_record.delete(leaf_start)
        self._find_key_in_leaf.delete(leaf_start)
        self._read_leaf_nr_of_elements.delete(leaf_start)
        self._read_leaf_nr_of_elements_and_neighbours.delete(leaf_start)

    def _insert_new_record_into_leaf(self, leaf_start, key, doc_id, start, size, status, nodes_stack, indexes):
        nr_of_elements = self._read_leaf_nr_of_elements(leaf_start)
        if nr_of_elements == 0:
            self.insert_first_record_into_leaf(
                leaf_start, key, doc_id, start, size, status)
            return
        leaf_start, new_record_position, nr_of_records_to_rewrite, full_leaf, on_deleted\
            = self._find_place_in_leaf(key, leaf_start, nr_of_elements)
        if full_leaf:
            try:  # check if leaf has parent node
                leaf_parent_pointer = nodes_stack.pop()
            except IndexError:  # leaf is a root
                leaf_parent_pointer = 0
            split_data = self._split_leaf(leaf_start,
                                          nr_of_records_to_rewrite,
                                          key,
                                          doc_id,
                                          start,
                                          size,
                                          status,
                                          create_new_root=(False if leaf_parent_pointer else True))
            if split_data is not None:  # means that split created new root or replaced split with update_if_has_deleted
                new_leaf_start_position, key_moved_to_parent_node = split_data
                self._insert_new_key_into_node(leaf_parent_pointer,
                                               key_moved_to_parent_node,
                                               leaf_start,
                                               new_leaf_start_position,
                                               nodes_stack,
                                               indexes)
        else:  # there is a place for record in leaf
            self.buckets.seek(leaf_start)
            self._update_leaf(
                leaf_start, new_record_position, nr_of_elements, nr_of_records_to_rewrite,
                on_deleted, key, doc_id, start, size, status)

    def _update_node(self, new_key_position, nr_of_keys_to_rewrite, new_key, new_pointer):
        if nr_of_keys_to_rewrite == 0:
            self.buckets.seek(new_key_position)
            self.buckets.write(
                struct.pack('<' + self.key_format + self.pointer_format,
                            new_key,
                            new_pointer))
            self.flush()
        else:
            self.buckets.seek(new_key_position)
            data = self.buckets.read(nr_of_keys_to_rewrite * (
                                     self.key_size + self.pointer_size))
            keys_to_rewrite = struct.unpack(
                '<' + nr_of_keys_to_rewrite * (self.key_format + self.pointer_format), data)
            self.buckets.seek(new_key_position)
            self.buckets.write(
                struct.pack(
                    '<' + (nr_of_keys_to_rewrite + 1) *
                    (self.key_format + self.pointer_format),
                    new_key,
                    new_pointer,
                    *keys_to_rewrite))
            self.flush()

    def _insert_new_key_into_node(self, node_start, new_key, old_half_start, new_half_start, nodes_stack, indexes):
        parent_key_index = indexes.pop()
        nr_of_elements, children_flag = self._read_node_nr_of_elements_and_children_flag(node_start)
        parent_prev_pointer = self._read_single_node_key(
            node_start, parent_key_index)[0]
        if parent_prev_pointer == old_half_start:  # splited child was on the left side of his parent key, must write new key before it
            new_key_position = self.pointer_size + self._calculate_key_position(node_start, parent_key_index, 'n')
            nr_of_keys_to_rewrite = nr_of_elements - parent_key_index
        else:  # splited child was on the right side of his parent key, must write new key after it
            new_key_position = self.pointer_size + self._calculate_key_position(node_start, parent_key_index + 1, 'n')
            nr_of_keys_to_rewrite = nr_of_elements - (parent_key_index + 1)
        if nr_of_elements == self.node_capacity:
            try:  # check if node has parent
                node_parent_pointer = nodes_stack.pop()
            except IndexError:  # node is a root
                node_parent_pointer = 0
            new_data = self._split_node(node_start,
                                        nr_of_keys_to_rewrite,
                                        new_key,
                                        new_half_start,
                                        children_flag,
                                        create_new_root=(False if node_parent_pointer else True))
            if new_data:  # if not new_data, new root has been created
                new_node_start_position, key_moved_to_parent_node = new_data
                self._insert_new_key_into_node(node_parent_pointer,
                                               key_moved_to_parent_node,
                                               node_start,
                                               new_node_start_position,
                                               nodes_stack,
                                               indexes)

            self._find_first_key_occurence_in_node.delete(node_start)
            self._find_last_key_occurence_in_node.delete(node_start)
        else:  # there is a empty slot for new key in node
            self._update_size(node_start, nr_of_elements + 1)
            self._update_node(new_key_position,
                              nr_of_keys_to_rewrite,
                              new_key,
                              new_half_start)

            self._find_first_key_occurence_in_node.delete(node_start)
            self._find_last_key_occurence_in_node.delete(node_start)
            self._read_single_node_key.delete(node_start)
            self._read_node_nr_of_elements_and_children_flag.delete(node_start)

    def _find_leaf_to_insert(self, key):
        """
        Traverses tree in search for leaf for insert, remembering parent nodes in path,
        looks for last occurence of key if already in tree.
        """
        nodes_stack = [self.data_start]
        if self.root_flag == 'l':
            return nodes_stack, []
        else:
            nr_of_elements, curr_child_flag = self._read_node_nr_of_elements_and_children_flag(self.data_start)
            curr_index, curr_pointer = self._find_last_key_occurence_in_node(
                self.data_start, key, nr_of_elements)
            nodes_stack.append(curr_pointer)
            indexes = [curr_index]
            while(curr_child_flag == 'n'):
                nr_of_elements, curr_child_flag = self._read_node_nr_of_elements_and_children_flag(curr_pointer)
                curr_index, curr_pointer = self._find_last_key_occurence_in_node(curr_pointer, key, nr_of_elements)
                nodes_stack.append(curr_pointer)
                indexes.append(curr_index)
            return nodes_stack, indexes
        # nodes stack contains start addreses of nodes directly above leaf with key, indexes match keys adjacent nodes_stack values (as pointers)
        # required when inserting new keys in upper tree levels

    def _find_leaf_with_last_key_occurence(self, key):
        if self.root_flag == 'l':
            return self.data_start
        else:
            nr_of_elements, curr_child_flag = self._read_node_nr_of_elements_and_children_flag(self.data_start)
            curr_position = self._find_last_key_occurence_in_node(
                self.data_start, key, nr_of_elements)[1]
            while(curr_child_flag == 'n'):
                nr_of_elements, curr_child_flag = self._read_node_nr_of_elements_and_children_flag(curr_position)
                curr_position = self._find_last_key_occurence_in_node(
                    curr_position, key, nr_of_elements)[1]
            return curr_position

    def _find_leaf_with_first_key_occurence(self, key):
        if self.root_flag == 'l':
            return self.data_start
        else:
            nr_of_elements, curr_child_flag = self._read_node_nr_of_elements_and_children_flag(self.data_start)
            curr_position = self._find_first_key_occurence_in_node(
                self.data_start, key, nr_of_elements)[1]
            while(curr_child_flag == 'n'):
                nr_of_elements, curr_child_flag = self._read_node_nr_of_elements_and_children_flag(curr_position)
                curr_position = self._find_first_key_occurence_in_node(
                    curr_position, key, nr_of_elements)[1]
            return curr_position

    def _find_key(self, key):
        containing_leaf_start = self._find_leaf_with_first_key_occurence(key)
        nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(containing_leaf_start)
        try:
            doc_id, l_key, start, size, status = self._find_key_in_leaf(
                containing_leaf_start, key, nr_of_elements)
        except ElemNotFound:
            if next_leaf:
                nr_of_elements = self._read_leaf_nr_of_elements(next_leaf)
            else:
                raise ElemNotFound
            doc_id, l_key, start, size, status = self._find_key_in_leaf(
                next_leaf, key, nr_of_elements)
        return doc_id, l_key, start, size, status

    def _find_key_to_update(self, key, doc_id):
        """
        Search tree for key that matches not only given key but also doc_id.
        """
        containing_leaf_start = self._find_leaf_with_first_key_occurence(key)
        nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(containing_leaf_start)
        try:
            leaf_start, record_index, doc_id, l_key, start, size, status = self._find_key_in_leaf_for_update(key,
                                                                                                             doc_id,
                                                                                                             containing_leaf_start,
                                                                                                             nr_of_elements)
        except ElemNotFound:
            if next_leaf:
                nr_of_elements = self._read_leaf_nr_of_elements(next_leaf)
            else:
                raise TryReindexException()
            try:
                leaf_start, record_index, doc_id, l_key, start, size, status = self._find_key_in_leaf_for_update(key,
                                                                                                                 doc_id,
                                                                                                                 next_leaf,
                                                                                                                 nr_of_elements)
            except ElemNotFound:
                raise TryReindexException()
        return leaf_start, record_index, doc_id, l_key, start, size, status

    def update(self, doc_id, key, u_start=0, u_size=0, u_status='o'):
        containing_leaf_start, element_index, old_doc_id, old_key, old_start, old_size, old_status = self._find_key_to_update(key, doc_id)
        new_data = (old_doc_id, old_start, old_size, old_status)
        if not u_start:
            new_data[1] = u_start
        if not u_size:
            new_data[2] = u_size
        if not u_status:
            new_data[3] = u_status
        self._update_element(containing_leaf_start, element_index, new_data)

        self._find_key.delete(key)
        self._match_doc_id.delete(doc_id)
        self._find_key_in_leaf.delete(containing_leaf_start, key)
        return True

    def delete(self, doc_id, key, start=0, size=0):
        containing_leaf_start, element_index = self._find_key_to_update(
            key, doc_id)[:2]
        self._delete_element(containing_leaf_start, element_index)

        self._find_key.delete(key)
        self._match_doc_id.delete(doc_id)
        self._find_key_in_leaf.delete(containing_leaf_start, key)
        return True

    def _find_key_many(self, key, limit=1, offset=0):
        leaf_with_key = self._find_leaf_with_first_key_occurence(key)
        nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
        try:
            leaf_with_key, key_index = self._find_index_of_first_key_equal(
                key, leaf_with_key, nr_of_elements)
            nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
        except ElemNotFound:
            leaf_with_key = next_leaf
            key_index = 0
            nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
        while offset:
            if key_index < nr_of_elements:
                curr_key, doc_id, start, size, status = self._read_single_leaf_record(
                    leaf_with_key, key_index)
                if key == curr_key:
                    if status != 'd':
                        offset -= 1
                    key_index += 1
                else:
                    return
            else:
                key_index = 0
                if next_leaf:
                    leaf_with_key = next_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(next_leaf)
                else:
                    return
        while limit:
            if key_index < nr_of_elements:
                curr_key, doc_id, start, size, status = self._read_single_leaf_record(
                    leaf_with_key, key_index)
                if key == curr_key:
                    if status != 'd':
                        yield doc_id, start, size, status
                        limit -= 1
                    key_index += 1
                else:
                    return
            else:
                key_index = 0
                if next_leaf:
                    leaf_with_key = next_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(next_leaf)
                else:
                    return

    def _find_key_smaller(self, key, limit=1, offset=0):
        leaf_with_key = self._find_leaf_with_first_key_occurence(key)
        nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
        leaf_with_key, key_index = self._find_index_of_first_key_equal_or_smaller_key(key, leaf_with_key, nr_of_elements)
        nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
        curr_key = self._read_single_leaf_record(leaf_with_key, key_index)[0]
        if curr_key >= key:
            key_index -= 1
        while offset:
            if key_index >= 0:
                key, doc_id, start, size, status = self._read_single_leaf_record(
                    leaf_with_key, key_index)
                if status != 'd':
                    offset -= 1
                key_index -= 1
            else:
                if prev_leaf:
                    leaf_with_key = prev_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(prev_leaf)
                    key_index = nr_of_elements - 1
                else:
                    return
        while limit:
            if key_index >= 0:
                key, doc_id, start, size, status = self._read_single_leaf_record(
                    leaf_with_key, key_index)
                if status != 'd':
                    yield doc_id, key, start, size, status
                    limit -= 1
                key_index -= 1
            else:
                if prev_leaf:
                    leaf_with_key = prev_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(prev_leaf)
                    key_index = nr_of_elements - 1
                else:
                    return

    def _find_key_equal_and_smaller(self, key, limit=1, offset=0):
        leaf_with_key = self._find_leaf_with_last_key_occurence(key)
        nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
        try:
            leaf_with_key, key_index = self._find_index_of_last_key_equal_or_smaller_key(key, leaf_with_key, nr_of_elements)
            nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
        except ElemNotFound:
            leaf_with_key = prev_leaf
            key_index = self._read_leaf_nr_of_elements_and_neighbours(
                leaf_with_key)[0]
        curr_key = self._read_single_leaf_record(leaf_with_key, key_index)[0]
        if curr_key > key:
            key_index -= 1
        while offset:
            if key_index >= 0:
                key, doc_id, start, size, status = self._read_single_leaf_record(
                    leaf_with_key, key_index)
                if status != 'd':
                    offset -= 1
                key_index -= 1
            else:
                if prev_leaf:
                    leaf_with_key = prev_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(prev_leaf)
                    key_index = nr_of_elements - 1
                else:
                    return
        while limit:
            if key_index >= 0:
                key, doc_id, start, size, status = self._read_single_leaf_record(
                    leaf_with_key, key_index)
                if status != 'd':
                    yield doc_id, key, start, size, status
                    limit -= 1
                key_index -= 1
            else:
                if prev_leaf:
                    leaf_with_key = prev_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(prev_leaf)
                    key_index = nr_of_elements - 1
                else:
                    return

    def _find_key_bigger(self, key, limit=1, offset=0):
        leaf_with_key = self._find_leaf_with_last_key_occurence(key)
        nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
        try:
            leaf_with_key, key_index = self._find_index_of_last_key_equal_or_smaller_key(key, leaf_with_key, nr_of_elements)
            nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
        except ElemNotFound:
            key_index = 0
        curr_key = self._read_single_leaf_record(leaf_with_key, key_index)[0]
        if curr_key <= key:
            key_index += 1
        while offset:
            if key_index < nr_of_elements:
                curr_key, doc_id, start, size, status = self._read_single_leaf_record(
                    leaf_with_key, key_index)
                if status != 'd':
                    offset -= 1
                key_index += 1
            else:
                key_index = 0
                if next_leaf:
                    leaf_with_key = next_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(next_leaf)
                else:
                    return
        while limit:
            if key_index < nr_of_elements:
                curr_key, doc_id, start, size, status = self._read_single_leaf_record(
                    leaf_with_key, key_index)
                if status != 'd':
                    yield doc_id, curr_key, start, size, status
                    limit -= 1
                key_index += 1
            else:
                key_index = 0
                if next_leaf:
                    leaf_with_key = next_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(next_leaf)
                else:
                    return

    def _find_key_equal_and_bigger(self, key, limit=1, offset=0):
        leaf_with_key = self._find_leaf_with_first_key_occurence(key)
        nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
        leaf_with_key, key_index = self._find_index_of_first_key_equal_or_smaller_key(key, leaf_with_key, nr_of_elements)
        nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
        curr_key = self._read_single_leaf_record(leaf_with_key, key_index)[0]
        if curr_key < key:
            key_index += 1
        while offset:
            if key_index < nr_of_elements:
                curr_key, doc_id, start, size, status = self._read_single_leaf_record(
                    leaf_with_key, key_index)
                if status != 'd':
                    offset -= 1
                key_index += 1
            else:
                key_index = 0
                if next_leaf:
                    leaf_with_key = next_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(next_leaf)
                else:
                    return
        while limit:
            if key_index < nr_of_elements:
                curr_key, doc_id, start, size, status = self._read_single_leaf_record(
                    leaf_with_key, key_index)
                if status != 'd':
                    yield doc_id, curr_key, start, size, status
                    limit -= 1
                key_index += 1
            else:
                key_index = 0
                if next_leaf:
                    leaf_with_key = next_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(next_leaf)
                else:
                    return

    def _find_key_between(self, start, end, limit, offset, inclusive_start, inclusive_end):
        """
        Returns generator containing all keys withing given interval.
        """
        if inclusive_start:
            leaf_with_key = self._find_leaf_with_first_key_occurence(start)
            nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
            leaf_with_key, key_index = self._find_index_of_first_key_equal_or_smaller_key(start, leaf_with_key, nr_of_elements)
            nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
            curr_key = self._read_single_leaf_record(
                leaf_with_key, key_index)[0]
            if curr_key < start:
                key_index += 1
        else:
            leaf_with_key = self._find_leaf_with_last_key_occurence(start)
            nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_with_key)
            leaf_with_key, key_index = self._find_index_of_last_key_equal_or_smaller_key(start, leaf_with_key, nr_of_elements)
            curr_key, curr_doc_id, curr_start, curr_size, curr_status = self._read_single_leaf_record(leaf_with_key, key_index)
            if curr_key <= start:
                key_index += 1
        while offset:
            if key_index < nr_of_elements:
                curr_key, curr_doc_id, curr_start, curr_size, curr_status = self._read_single_leaf_record(leaf_with_key, key_index)
                if curr_status != 'd':
                    offset -= 1
                key_index += 1
            else:
                key_index = 0
                if next_leaf:
                    leaf_with_key = next_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(next_leaf)
                else:
                    return
        while limit:
            if key_index < nr_of_elements:
                curr_key, curr_doc_id, curr_start, curr_size, curr_status = self._read_single_leaf_record(leaf_with_key, key_index)
                if curr_key > end or (curr_key == end and not inclusive_end):
                    return
                elif curr_status != 'd':
                    yield curr_doc_id, curr_key, curr_start, curr_size, curr_status
                    limit -= 1
                key_index += 1
            else:
                key_index = 0
                if next_leaf:
                    leaf_with_key = next_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(next_leaf)
                else:
                    return

    def get(self, key):
        return self._find_key(self.make_key(key))

    def get_many(self, key, limit=1, offset=0):
        return self._find_key_many(self.make_key(key), limit, offset)

    def get_between(self, start, end, limit=1, offset=0, inclusive_start=True, inclusive_end=True):
        if start is None:
            end = self.make_key(end)
            if inclusive_end:
                return self._find_key_equal_and_smaller(end, limit, offset)
            else:
                return self._find_key_smaller(end, limit, offset)
        elif end is None:
            start = self.make_key(start)
            if inclusive_start:
                return self._find_key_equal_and_bigger(start, limit, offset)
            else:
                return self._find_key_bigger(start, limit, offset)
        else:
            start = self.make_key(start)
            end = self.make_key(end)
            return self._find_key_between(start, end, limit, offset, inclusive_start, inclusive_end)

    def all(self, limit=-1, offset=0):
        """
        Traverses linked list of all tree leaves and returns generator containing all elements stored in index.
        """
        if self.root_flag == 'n':
            leaf_start = self.data_start + self.node_size
        else:
            leaf_start = self.data_start
        nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(leaf_start)
        key_index = 0
        while offset:
            if key_index < nr_of_elements:
                curr_key, doc_id, start, size, status = self._read_single_leaf_record(
                    leaf_start, key_index)
                if status != 'd':
                    offset -= 1
                key_index += 1
            else:
                key_index = 0
                if next_leaf:
                    leaf_start = next_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(next_leaf)
                else:
                    return
        while limit:
            if key_index < nr_of_elements:
                curr_key, doc_id, start, size, status = self._read_single_leaf_record(
                    leaf_start, key_index)
                if status != 'd':
                    yield doc_id, curr_key, start, size, status
                    limit -= 1
                key_index += 1
            else:
                key_index = 0
                if next_leaf:
                    leaf_start = next_leaf
                    nr_of_elements, prev_leaf, next_leaf = self._read_leaf_nr_of_elements_and_neighbours(next_leaf)
                else:
                    return

    def make_key(self, key):
        raise NotImplementedError()

    def make_key_value(self, data):
        raise NotImplementedError()

    def _open_storage(self):
        s = globals()[self.storage_class]
        if not self.storage:
            self.storage = s(self.db_path, self.name)
        self.storage.open()

    def _create_storage(self):
        s = globals()[self.storage_class]
        if not self.storage:
            self.storage = s(self.db_path, self.name)
        self.storage.create()

    def compact(self, node_capacity=0):
        if not node_capacity:
            node_capacity = self.node_capacity

        compact_ind = self.__class__(
            self.db_path, self.name + '_compact', node_capacity=node_capacity)
        compact_ind.create_index()

        gen = self.all()
        while True:
            try:
                doc_id, key, start, size, status = gen.next()
            except StopIteration:
                break
            self.storage._f.seek(start)
            value = self.storage._f.read(size)
            start_ = compact_ind.storage._f.tell()
            compact_ind.storage._f.write(value)
            compact_ind.insert(doc_id, key, start_, size, status)

        compact_ind.close_index()
        original_name = self.name
        # os.unlink(os.path.join(self.db_path, self.name + "_buck"))
        self.close_index()
        shutil.move(os.path.join(compact_ind.db_path, compact_ind.
                                 name + "_buck"), os.path.join(self.db_path, self.name + "_buck"))
        shutil.move(os.path.join(compact_ind.db_path, compact_ind.
                                 name + "_stor"), os.path.join(self.db_path, self.name + "_stor"))
        # self.name = original_name
        self.open_index()  # reload...
        self.name = original_name
        self._save_params(dict(name=original_name))
        self._fix_params()
        self._clear_cache()
        return True

    def _fix_params(self):
        super(IU_TreeBasedIndex, self)._fix_params()
        self._count_props()

    def _clear_cache(self):
        self._find_key.clear()
        self._match_doc_id.clear()
#        self._read_single_leaf_record.clear()
        self._find_key_in_leaf.clear()
        self._read_single_node_key.clear()
        self._find_first_key_occurence_in_node.clear()
        self._find_last_key_occurence_in_node.clear()
        self._read_leaf_nr_of_elements.clear()
        self._read_leaf_neighbours.clear()
        self._read_leaf_nr_of_elements_and_neighbours.clear()
        self._read_node_nr_of_elements_and_children_flag.clear()

    def close_index(self):
        super(IU_TreeBasedIndex, self).close_index()
        self._clear_cache()


class IU_MultiTreeBasedIndex(IU_TreeBasedIndex):
    """
    Class that allows to index more than one key per database record.

    It operates very well on GET/INSERT. It's not optimized for
    UPDATE operations (will always readd everything)
    """

    def __init__(self, *args, **kwargs):
        super(IU_MultiTreeBasedIndex, self).__init__(*args, **kwargs)

    def insert(self, doc_id, key, start, size, status='o'):
        if isinstance(key, (list, tuple)):
            key = set(key)
        elif not isinstance(key, set):
            key = set([key])
        ins = super(IU_MultiTreeBasedIndex, self).insert
        for curr_key in key:
            ins(doc_id, curr_key, start, size, status)
        return True

    def update(self, doc_id, key, u_start, u_size, u_status='o'):
        if isinstance(key, (list, tuple)):
            key = set(key)
        elif not isinstance(key, set):
            key = set([key])
        upd = super(IU_MultiTreeBasedIndex, self).update
        for curr_key in key:
            upd(doc_id, curr_key, u_start, u_size, u_status)

    def delete(self, doc_id, key, start=0, size=0):
        if isinstance(key, (list, tuple)):
            key = set(key)
        elif not isinstance(key, set):
            key = set([key])
        delete = super(IU_MultiTreeBasedIndex, self).delete
        for curr_key in key:
            delete(doc_id, curr_key, start, size)

    def get(self, key):
        return super(IU_MultiTreeBasedIndex, self).get(key)

    def make_key_value(self, data):
        raise NotImplementedError()


# classes for public use, done in this way because of
# generation static files with indexes (_index directory)


class TreeBasedIndex(IU_TreeBasedIndex):
    pass


class MultiTreeBasedIndex(IU_MultiTreeBasedIndex):
    """
    It allows to index more than one key for record. (ie. prefix/infix/suffix search mechanizms)
    That class is designed to be used in custom indexes.
    """
    pass

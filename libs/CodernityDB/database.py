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

import os
import io
from inspect import getsource

# for custom indexes
from CodernityDB.storage import Storage, IU_Storage
from CodernityDB.hash_index import (IU_UniqueHashIndex,
                                    IU_HashIndex,
                                    HashIndex,
                                    UniqueHashIndex)
# normal imports

from CodernityDB.index import (ElemNotFound,
                               DocIdNotFound,
                               IndexException,
                               Index,
                               TryReindexException,
                               ReindexException,
                               IndexNotFoundException,
                               IndexConflict)

from CodernityDB.misc import NONE

from CodernityDB.env import cdb_environment

from random import randrange

import warnings


def header_for_indexes(index_name, index_class, db_custom="", ind_custom="", classes_code=""):
    return """# %s
# %s

# inserted automatically
import os
import marshal

import struct
import shutil

from hashlib import md5

# custom db code start
# db_custom
%s

# custom index code start
# ind_custom
%s

# source of classes in index.classes_code
# classes_code
%s

# index code start

""" % (index_name, index_class, db_custom, ind_custom, classes_code)


class DatabaseException(Exception):
    pass


class PreconditionsException(DatabaseException):
    pass


class RecordDeleted(DatabaseException):
    pass


class RecordNotFound(DatabaseException):
    pass


class RevConflict(DatabaseException):
    pass


class DatabaseConflict(DatabaseException):
    pass


class DatabasePathException(DatabaseException):
    pass


class DatabaseIsNotOpened(PreconditionsException):
    pass


class Database(object):
    """
    A default single thread database object.
    """

    custom_header = ""  # : use it for imports required by your database

    def __init__(self, path):
        self.path = path
        self.storage = None
        self.indexes = []
        self.id_ind = None
        self.indexes_names = {}
        self.opened = False

    def create_new_rev(self, old_rev=None):
        """
        Creates new revision number based on previous one.
        Increments it + random bytes. On overflow starts from 0 again.
        """
        if old_rev:
            try:
                rev_num = int(old_rev[:4], 16)
            except:
                raise RevConflict()
            rev_num += 1
            if rev_num > 65025:
            # starting the counter from 0 again
                rev_num = 0
            rnd = randrange(65536)
            return "%04x%04x" % (rev_num, rnd)
        else:
            # new rev
            rnd = randrange(256 ** 2)
            return '0001%04x' % rnd

    def __not_opened(self):
        if not self.opened:
            raise DatabaseIsNotOpened("Database is not opened")

    def set_indexes(self, indexes=[]):
        """
        Set indexes using ``indexes`` param

        :param indexes: indexes to set in db
        :type indexes: iterable of :py:class:`CodernityDB.index.Index` objects.

        """
        for ind in indexes:
            self.add_index(ind, create=False)

    def _add_single_index(self, p, i, index):
        """
        Adds single index to a database.
        It will use :py:meth:`inspect.getsource` to get class source.
        Then it will build real index file, save it in ``_indexes`` directory.
        """
        code = getsource(index.__class__)
        if not code.startswith('c'):  # fix for indented index codes
            import textwrap
            code = textwrap.dedent(code)
        index._order = i
        cls_code = getattr(index, 'classes_code', [])
        classes_code = ""
        for curr in cls_code:
            classes_code += getsource(curr) + '\n\n'
        with io.FileIO(os.path.join(p, "%.2d%s" % (i, index.name) + '.py'), 'w') as f:
            f.write(header_for_indexes(index.name,
                                       index.__class__.__name__,
                                       getattr(self, 'custom_header', ''),
                                       getattr(index, 'custom_header', ''),
                                       classes_code))
            f.write(code)
        return True

    def _read_index_single(self, p, ind, ind_kwargs={}):
        """
        It will read single index from index file (ie. generated in :py:meth:`._add_single_index`).
        Then it will perform ``exec`` on that code

        If error will occur the index file will be saved with ``_broken`` suffix

        :param p: path
        :param ind: index name (will be joined with *p*)
        :returns: new index object
        """
        with io.FileIO(os.path.join(p, ind), 'r') as f:
            name = f.readline()[2:].strip()
            _class = f.readline()[2:].strip()
            code = f.read()
        try:
            obj = compile(code, '<Index: %s' % os.path.join(p, ind), 'exec')
            exec obj in globals()
            ind_obj = globals()[_class](self.path, name, **ind_kwargs)
            ind_obj._order = int(ind[:2])
        except:
            ind_path = os.path.join(p, ind)
            os.rename(ind_path, ind_path + '_broken')  # rename it instead of removing
#            os.unlink(os.path.join(p, ind))
            warnings.warn("Fatal error in index, saved as %s" % (ind_path + '_broken', ))
            raise
        else:
            return ind_obj

    def __check_if_index_unique(self, name, num):
        indexes = os.listdir(os.path.join(self.path, '_indexes'))
        if any((x for x in indexes if x[2:-3] == name and x[:2] != str(num))):
            raise IndexConflict("Already exists")

    def __write_index(self, new_index, number=0, edit=False, ind_kwargs=None):
        # print new_index
        if ind_kwargs is None:
            ind_kwargs = {}
        p = os.path.join(self.path, '_indexes')
        if isinstance(new_index, basestring) and not new_index.startswith("path:"):
            if len(new_index.splitlines()) < 4 or new_index.splitlines()[3] != '# inserted automatically':
                from indexcreator import Parser
                par = Parser()
                custom_imports, s = par.parse(new_index)
                s = s.splitlines()
                name = s[0][2:]
                c = s[1][2:]
                comented = ['\n\n#SIMPLIFIED CODE']
                map(lambda x: comented.append("#" + x), new_index.splitlines())
                comented.append('#SIMPLIFIED CODE END\n\n')

                s = header_for_indexes(
                    name, c, ind_custom=custom_imports) + "\n".join(s[2:]) + "\n".join(comented)
                new_index = s
            else:
                name = new_index.splitlines()[0][2:]
                name = name.strip()

            if name in self.indexes_names and not edit:
                raise IndexConflict("Already exists")
            if edit:
                previous_index = filter(lambda x: x.endswith(
                    '.py') and x[2:-3] == name, os.listdir(p))
                if not previous_index:
                    raise PreconditionsException(
                        "Can't edit index that's not yet in database")
                number = int(previous_index[0][:2])
            if number == 0 and not edit and not name == 'id':
                raise PreconditionsException(
                    "Id index must be the first added")
            ind_path = "%.2d%s" % (number, name)
            if not edit:
                self.__check_if_index_unique(name, number)

            ind_path_f = os.path.join(p, ind_path + '.py')
            if os.path.exists(ind_path_f):
                os.rename(ind_path_f, ind_path_f + '_last')  # save last working index code
            with io.FileIO(ind_path_f, 'w') as f:
                f.write(new_index)

            ind_obj = self._read_index_single(p, ind_path + '.py')

        elif isinstance(new_index, basestring) and new_index.startswith("path:"):
            path = new_index[5:]
            if not path.endswith('.py'):
                path += '.py'
            ind_obj = self._read_index_single(p, path, ind_kwargs)
            name = ind_obj.name
            if name in self.indexes_names and not edit:
                raise IndexConflict("Already exists")
        elif isinstance(new_index, Index):
            # it will first save index as a string, and then compile it
            # it will allow to control the index object on the DB side
            ind = new_index
            init_arguments = new_index.__class__.__init__.im_func.func_code.co_varnames[
                3:]  # ignore self, path and name
            for curr in init_arguments:
                if curr not in ('args', 'kwargs'):
                    v = getattr(ind, curr, NONE())
                    if not isinstance(v, NONE):
                        ind_kwargs[curr] = v
            if edit:
                # code duplication...
                previous_index = filter(lambda x: x.endswith(
                    '.py') and x[2:-3] == ind.name, os.listdir(p))
                if not previous_index:
                    raise PreconditionsException(
                        "Can't edit index that's not yet in database")
                number = int(previous_index[0][:2])
            if ind.name in self.indexes_names and not edit:
                raise IndexConflict("Already exists")
            if number == 0 and not edit and not ind.name == 'id':
                raise PreconditionsException(
                    "Id index must be the first added")
            if not edit:
                self.__check_if_index_unique(ind.name, number)
            self._add_single_index(p, number, ind)
            ind_path = "%.2d%s" % (number, ind.name)
            ind_obj = self._read_index_single(p, ind_path + '.py', ind_kwargs)
            name = ind_obj.name
        else:
            raise PreconditionsException("Argument must be Index instance, path to index_file or valid string index format")
        return ind_obj, name

    def add_index(self, new_index, create=True, ind_kwargs=None):
        """

        :param new_index: New index to add, can be Index object, index valid string or path to file with index code
        :type new_index: string
        :param create: Create the index after add or not
        :type create: bool

        :returns: new index name
        """

        if ind_kwargs is None:
            ind_kwargs = {}
        p = os.path.join(self.path, '_indexes')
        if not os.path.exists(p):
            self.initialize()
        current = sorted(filter(lambda x: x.endswith('.py'), os.listdir(p)))
        if current:
            last = int(current[-1][:2])  # may crash... ignore
            _next = last + 1
        else:
            _next = 0
        ind_obj, name = self.__write_index(new_index, _next, edit=False)
        # add the new index to objects
        self.indexes.append(ind_obj)
        self.indexes_names[name] = ind_obj
        if create:
            if self.exists():  # no need te create if database doesn't exists'
                ind_obj.create_index()
        if name == 'id':
            self.__set_main_storage()
            self.__compat_things()
        for patch in getattr(ind_obj, 'patchers', ()):  # index can patch db object
            patch(self)
        return name

    def edit_index(self, index, reindex=False, ind_kwargs=None):
        """
        Allows to edit existing index.
        Previous working version will be saved with ``_last`` suffix (see :py:meth:`.revert_index`

        :param bool reindex: should be the index reindexed after change

        :returns: index name
        """
        if ind_kwargs is None:
            ind_kwargs = {}
        ind_obj, name = self.__write_index(index, -1, edit=True)
        old = next(x for x in self.indexes if x.name == name)
        old.close_index()
        index_of_index = self.indexes.index(old)
        ind_obj.open_index()
        self.indexes[index_of_index] = ind_obj
        self.indexes_names[name] = ind_obj
        if reindex:
            self.reindex_index(name)
        return name

    def revert_index(self, index_name, reindex=False, ind_kwargs=None):
        """
        Tries to revert index code from copy.
        It calls :py:meth:`.edit_index` with previous working.

        :param string index_name: index name to restore
        """
        ind_path = os.path.join(self.path, '_indexes')
        if index_name in self.indexes_names:  # then it's working index.
            ind = self.indexes_names[index_name]
            full_name = '%.2d%s.py' % (ind._order, index_name)
        else:
            indexes = os.listdir(ind_path)
            full_name = next((x for x in indexes if x[2:-3] == index_name))
        if not full_name:
            raise DatabaseException("%s index not found" % index_name)
        last_path = os.path.join(ind_path, full_name + "_last")
        if not os.path.exists(last_path):
            raise DatabaseException("No previous copy found for %s" % index_name)
        correct_last_path = last_path[:-5]  # remove _last from name
        os.rename(last_path, correct_last_path)
#        ind_data = open(last_path, 'r')
        p = 'path:%s' % os.path.split(correct_last_path)[1]
        return self.edit_index(p, reindex, ind_kwargs)

    def get_index_code(self, index_name, code_switch='All'):
        """
        It will return full index code from index file.

        :param index_name: the name of index to look for code
        """
        if not index_name in self.indexes_names:
            self.__not_opened()
            raise IndexNotFoundException(
                "Index `%s` doesn't exists" % index_name)
        ind = self.indexes_names[index_name]
        name = "%.2d%s" % (ind._order, index_name)
        name += '.py'
        with io.FileIO(os.path.join(self.path, '_indexes', name), 'r') as f:
            co = f.read()
            if code_switch == 'All':
                return co

            if code_switch == 'S':
                try:
                    ind = co.index('#SIMPLIFIED CODE')
                except ValueError:
                    return " "
                else:
                    s = co[ind:]
                    l = s.splitlines()[1:-2]
                    ll = map(lambda x: x[1:], l)
                    return '\n'.join(ll)
            if code_switch == 'P':
                try:
                    ind = co.index('#SIMPLIFIED CODE')
                except ValueError:
                    return co
                else:
                    return co[:ind]

        return ""  # shouldn't happen

    def __set_main_storage(self):
        """
        Sets database main storage (from the **id** index)
        """
        try:
            self.storage = self.indexes_names['id'].storage
            self.id_ind = self.indexes_names['id']
        except KeyError:
            # when opening / initializing DB without `id` index
            # happens mostly on server side
            pass

    def initialize(self, path=None, makedir=True):
        """
        Initialize new database

        :param path: Path to a database (allows delayed path configuration), if not provided self.path will be used
        :param makedir: Make the ``_indexes`` directory or not

        :returns: the database path
        """
        if self.opened is True:
            raise DatabaseConflict("Already opened")
        if not path:
            path = self.path
        else:
            self.path = path
        if makedir:
            if not self.path:
                raise PreconditionsException("No path specified")
            p = os.path.join(self.path, '_indexes')
            if os.path.exists(p):
                raise DatabaseConflict("Cant't create because already exists")
            os.makedirs(p)

        return self.path

    def __open_new(self, with_id_index=True, index_kwargs={}):
        """
        Will open new database (works like create),
        if not self.path provided will call initialize()
        """
        if self.path:
            if not os.path.exists(self.path):
                self.initialize(self.path)
        if not 'id' in self.indexes_names and with_id_index:
            import CodernityDB.hash_index
            if not 'db_path' in index_kwargs:
                index_kwargs['db_path'] = self.path
            index_kwargs['name'] = 'id'
            id_ind = CodernityDB.hash_index.UniqueHashIndex(**index_kwargs)
            self.add_index(id_ind, create=False)
            # del CodernityDB.index
        for index in self.indexes:
            try:
                index.create_index()
            except IndexException:
                raise DatabaseConflict(
                    "Already exists (detected on index=%s)" % index.name)
        return True

    def _read_indexes(self):
        """
        Read all known indexes from ``_indexes``
        """
        p = os.path.join(self.path, '_indexes')
        for ind in os.listdir(p):
            if ind.endswith('.py'):
                self.add_index('path:' + ind, create=False)

    def __compat_things(self):
        """
        Things for compatibility.
        """
        # patch for rev size change
        if not self.id_ind:
            return
        if self.id_ind.entry_line_format[4:6] == '4s':
            # rev compatibility...
            warnings.warn("Your database is using old rev mechanizm \
for ID index. You should update that index \
(CodernityDB.migrate.migrate).")
            from misc import random_hex_4
            self.create_new_rev = random_hex_4

    def create(self, path=None, **kwargs):
        """
        Create database

        :param path: path where to create the database

        :returns: database path
        """
        if path:
            self.initialize(path)
        if not self.path:
            raise PreconditionsException("No path specified")
        if self.opened is True:
            raise DatabaseConflict("Already opened")
        self.__open_new(**kwargs)
        self.__set_main_storage()
        self.__compat_things()
        self.opened = True
        return self.path

    def exists(self, path=None):
        """
        Checks if database in given path exists

        :param path: path to look for database
        """
        if not path:
            path = self.path
        if not path:
            return False
        if os.path.exists(path):
            return os.path.exists(os.path.join(path, '_indexes'))
        return False

    def open(self, path=None):
        """
        Will open already existing database

        :param path: path with database to open
        """
        if self.opened is True:
            raise DatabaseConflict("Already opened")
#        else:
        if path:
            self.path = path
        if not self.path:
            raise PreconditionsException("No path specified")
        if not os.path.exists(self.path):
            raise DatabasePathException("Can't open database")
        self.indexes = []
        self.id_ind = None
        self.indexes_names = {}
        self._read_indexes()
        if not 'id' in self.indexes_names:
            raise PreconditionsException("There must be `id` index!")
        for index in self.indexes:
            index.open_index()
        self.indexes.sort(key=lambda ind: ind._order)
        self.__set_main_storage()
        self.__compat_things()
        self.opened = True
        return True

    def close(self):
        """
        Closes the database
        """
        if not self.opened:
            raise DatabaseConflict("Not opened")
        self.id_ind = None
        self.indexes_names = {}
        self.storage = None
        for index in self.indexes:
            index.close_index()
        self.indexes = []
        self.opened = False
        return True

    def destroy(self):
        """
        Allows to destroy database.

        **not reversable** operation!
        """
        # destroy all but *id*
        if not self.exists():
            raise DatabaseConflict("Doesn't exists'")
        for index in reversed(self.indexes[1:]):
            try:
                self.destroy_index(index)
            except:
                pass
        if getattr(self, 'id_ind', None) is not None:
            self.id_ind.destroy()  # now destroy id index
        # remove all files in db directory
        for root, dirs, files in os.walk(self.path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.path)
        self.close()
        return True

    def _single_update_index(self, index, data, db_data, doc_id):
        """
        Performs update operation on single index

        :param index: the index to perform operation
        :param data: new data
        :param db_data: database data
        :param doc_id: the id of document
        """
        try:
            old_should_index = index.make_key_value(db_data)
        except Exception as ex:
            warnings.warn("""Problem during update for `%s`, ex = `%s`, \
uou should check index code.""" % (index.name, ex), RuntimeWarning)
            old_should_index = None
        if old_should_index:
            old_key, old_value = old_should_index
            try:
                new_should_index = index.make_key_value(data)
            except Exception as ex:
                warnings.warn("""Problem during update for `%s`, ex = `%r`, \
you should check index code.""" % (index.name, ex), RuntimeWarning)
                new_should_index = None
            if new_should_index:
                new_key, new_value = new_should_index
                if new_key != old_key:
                    index.delete(doc_id, old_key)
                    index.insert_with_storage(doc_id, new_key, new_value)
                elif new_value != old_value:
                    try:
                        index.update_with_storage(doc_id, new_key, new_value)
                    except (ElemNotFound, DocIdNotFound):
                        # element should be in index but isn't
                        #(propably added new index without reindex)
                        warnings.warn("""Reindex might be required for index %s""" % index.name)
            else:
                index.delete(doc_id, old_key)
        else:  # not previously indexed
            self._single_insert_index(index, data, doc_id)

    def _update_id_index(self, _rev, data):
        """
        Performs update on **id** index
        """
        _id, value = self.id_ind.make_key_value(data)
        db_data = self.get('id', _id)
        if db_data['_rev'] != _rev:
            raise RevConflict()
        new_rev = self.create_new_rev(_rev)
        # storage = self.storage
        # start, size = storage.update(value)
        # self.id_ind.update(_id, new_rev, start, size)
        self.id_ind.update_with_storage(_id, new_rev, value)
        return _id, new_rev, db_data

    def _update_indexes(self, _rev, data):
        """
        Performs update operation on all indexes in order
        """
        _id, new_rev, db_data = self._update_id_index(_rev, data)
        for index in self.indexes[1:]:
            self._single_update_index(index, data, db_data, _id)
        return _id, new_rev

    def _single_insert_index(self, index, data, doc_id):
        """
        Performs insert operation on single index

        :param index: index to perform operation
        :param data: new data
        :param doc_id: document id
        """
        try:
            should_index = index.make_key_value(data)
        except Exception as ex:
            warnings.warn("""Problem during insert for `%s`, ex = `%r`, \
you should check index code.""" % (index.name, ex), RuntimeWarning)
            should_index = None
        if should_index:
            key, value = should_index
            index.insert_with_storage(doc_id, key, value)
            # if value:
            #     storage = index.storage
            #     start, size = storage.insert(value)
            # else:
            #     start = 1
            #     size = 0
            # index.insert(doc_id, key, start, size)

    def _insert_id_index(self, _rev, data):
        """
        Performs insert on **id** index.
        """
        _id, value = self.id_ind.make_key_value(data)  # may be improved
#        storage = self.storage
        # start, size = storage.insert(value)
        # self.id_ind.insert(_id, _rev, start, size)
        self.id_ind.insert_with_storage(_id, _rev, value)
        return _id

    def _insert_indexes(self, _rev, data):
        """
        Performs insert operation on all indexes in order
        """
        _id = self._insert_id_index(_rev, data)
        for index in self.indexes[1:]:
            self._single_insert_index(index, data, _id)

    def _single_delete_index(self, index, data, doc_id, old_data):
        """
        Performs single delete operation on single index.
        It's very similar to update functions (that's why data is in arguments)

        :param index: index to perform operation
        :param data: not important (because of update operations)
        :param doc_id: document id
        :param old_data: current data in database
        """
        index_data = index.make_key_value(old_data)
        if not index_data:
            return
        key, value = index_data
        try:
            index.delete(doc_id, key)
        except TryReindexException:
            return

    def _delete_id_index(self, _id, _rev, data):
        """
        Performs delete from **id** index
        """
        # key, value = self.id_ind.make_key_value(data)
        # key = data['_id']
        key = self.id_ind.make_key(_id)
        self.id_ind.delete(key)

    def _delete_indexes(self, _id, _rev, data):
        """
        Performs delete operation on all indexes in order
        """
        old_data = self.get('id', _id)
        if old_data['_rev'] != _rev:
            raise RevConflict()
        for index in self.indexes[1:]:
            self._single_delete_index(index, data, _id, old_data)
        self._delete_id_index(_id, _rev, data)

    def destroy_index(self, index):
        """
        Destroys index

        :param index: the index to destroy
        :type index: :py:class:`CodernityDB.index.Index`` instance, or string
        """
        if isinstance(index, basestring):
            if not index in self.indexes_names:
                raise PreconditionsException("No index named %s" % index)
            index = self.indexes_names[index]
        elif not index in self.indexes:
            self.__not_opened()
            raise PreconditionsException("Argument must be Index instance or valid string index format")
        if index.name == 'id':
            self.__not_opened()
            raise PreconditionsException("Id index cannot be destroyed")
        full_file = "%.2d%s" % (index._order, index.name) + '.py'
        p = os.path.join(self.path, '_indexes', full_file)
        os.unlink(p)
        index.destroy()
        del self.indexes_names[index.name]
        self.indexes.remove(index)

    def compact_index(self, index):
        """
        Compacts index
        Used for better utilization of index metadata.
        The deleted documents will be not more in structure.

        :param index: the index to destroy
        :type index: :py:class:`CodernityDB.index.Index`` instance, or string
        """
        if isinstance(index, basestring):
            if not index in self.indexes_names:
                raise PreconditionsException("No index named %s" % index)
            index = self.indexes_names[index]
        elif not index in self.indexes:
            self.__not_opened()
            raise PreconditionsException("Argument must be Index instance or valid string index format")
        if getattr(index, 'compacting', False):
            raise ReindexException(
                "The index=%s is still compacting" % index.name)
        index.compacting = True
        index.compact()
        del index.compacting

    def _compact_indexes(self):
        """
        Runs compact on all indexes
        """
        for index in self.indexes:
            self.compact_index(index)

    def _single_reindex_index(self, index, data):
        doc_id, rev, start, size, status = self.id_ind.get(
            data['_id'])  # it's cached so it's ok
        if status != 'd' and status != 'u':
            self._single_insert_index(index, data, doc_id)

    def reindex_index(self, index):
        """
        Performs reindex on index. Optimizes metadata and storage informations for given index.

        You can't reindex **id** index.

        :param index: the index to reindex
        :type index: :py:class:`CodernityDB.index.Index`` instance, or string
        """
        if isinstance(index, basestring):
            if not index in self.indexes_names:
                raise PreconditionsException("No index named %s" % index)
            index = self.indexes_names[index]
        elif not index in self.indexes:
            self.__not_opened()
            raise PreconditionsException("Argument must be Index instance or valid string index format")
        if index.name == 'id':
            self.__not_opened()
            raise PreconditionsException("Id index cannot be reindexed")
        if getattr(index, 'reindexing', False):
            raise ReindexException(
                "The index=%s is still reindexing" % index.name)

        all_iter = self.all('id')
        index.reindexing = True
        index.destroy()
        index.create_index()

        while True:
            try:
                curr = all_iter.next()
            except StopIteration:
                break
            else:
                self._single_reindex_index(index, curr)
        del index.reindexing

    def _reindex_indexes(self):
        for index in self.indexes[1:]:
            self.reindex_index(index)

    def insert(self, data):
        """
        It's using **reference** on the given data dict object,
        to avoid it copy it before inserting!

        If data **will not** have ``_id`` field,
        it will be generated (random 32 chars string)

        :param data: data to insert
        """
        if '_rev' in data:
            self.__not_opened()
            raise PreconditionsException(
                "Can't add record with forbidden fields")
        _rev = self.create_new_rev()
        if not '_id' in data:
            try:
                _id = self.id_ind.create_key()
            except:
                self.__not_opened()
                raise DatabaseException("No id?")
        else:
            _id = data['_id']
        assert _id is not None
        data['_rev'] = _rev  # for make_key_value compat with update / delete
        data['_id'] = _id
        self._insert_indexes(_rev, data)
        ret = {'_id': _id, '_rev': _rev}
        data.update(ret)
        return ret

    def update(self, data):
        """
        It's using **reference** on the given data dict object,
        to avoid it copy it before updating!

        ``data`` **must** contain ``_id`` and ``_rev`` fields.

        :param data: data to update
        """
        if not '_rev' in data or not '_id' in data:
            self.__not_opened()
            raise PreconditionsException("Can't update without _rev or _id")
        _rev = data['_rev']
        try:
            _rev = bytes(_rev)
        except:
            self.__not_opened()
            raise PreconditionsException(
                "`_rev` must be valid bytes object")
        _id, new_rev = self._update_indexes(_rev, data)
        ret = {'_id': _id, '_rev': new_rev}
        data.update(ret)
        return ret

    def get(self, index_name, key, with_doc=False, with_storage=True):
        """
        Get single data from Database by ``key``.

        :param index_name: index to get data from
        :param key: key to get
        :param with_doc: if ``True`` data from **id** index will be included in output
        :param with_storage: if ``True`` data from index storage will be included, otherwise just metadata.
        """
        # if not self.indexes_names.has_key(index_name):
        #     raise DatabaseException, "Invalid index name"
        try:
            ind = self.indexes_names[index_name]
        except KeyError:
            self.__not_opened()
            raise IndexNotFoundException(
                "Index `%s` doesn't exists" % index_name)
        try:
            l_key, _unk, start, size, status = ind.get(key)
        except ElemNotFound as ex:
            raise RecordNotFound(ex)
        if not start and not size:
            raise RecordNotFound("Not found")
        elif status == 'd':
            raise RecordDeleted("Deleted")
        if with_storage and size:
            storage = ind.storage
            data = storage.get(start, size, status)
        else:

            data = {}
        if with_doc and index_name != 'id':
            storage = ind.storage
            doc = self.get('id', l_key, False)
            if data:
                data['doc'] = doc
            else:
                data = {'doc': doc}
        data['_id'] = l_key
        if index_name == 'id':
            data['_rev'] = _unk
        else:
            data['key'] = _unk
        return data

    def get_many(self, index_name, key=None, limit=-1, offset=0, with_doc=False, with_storage=True, start=None, end=None, **kwargs):
        """
        Allows to get **multiple** data for given ``key`` for *Hash based indexes*.
        Also allows get **range** queries for *Tree based indexes* with ``start`` and ``end`` arguments.

        :param index_name: Index to perform the operation
        :param key: key to look for (has to be ``None`` to use range queries)
        :param limit: defines limit for query
        :param offset: defines offset (how many records from start it will ignore)
        :param with_doc: if ``True`` data from **id** index will be included in output
        :param with_storage: if ``True`` data from index storage will be included, otherwise just metadata.
        :param start: ``start`` parameter for range queries
        :param end: ``end`` parameter for range queries

        :returns: iterator over records
        """
        if index_name == 'id':
            self.__not_opened()
            raise PreconditionsException("Can't get many from `id`")
        try:
            ind = self.indexes_names[index_name]
        except KeyError:
            self.__not_opened()
            raise IndexNotFoundException(
                "Index `%s` doesn't exists" % index_name)
        storage = ind.storage
        if start is None and end is None:
            gen = ind.get_many(key, limit, offset)
        else:
            gen = ind.get_between(start, end, limit, offset, **kwargs)
        while True:
            try:
#                l_key, start, size, status = gen.next()
                ind_data = gen.next()
            except StopIteration:
                break
            else:
                if with_storage and ind_data[-2]:
                    data = storage.get(*ind_data[-3:])
                else:
                    data = {}
                doc_id = ind_data[0]
                if with_doc:
                    doc = self.get('id', doc_id, False)
                    if data:
                        data['doc'] = doc
                    else:
                        data = {'doc': doc}
                data['_id'] = doc_id
                if key is None:
                    data['key'] = ind_data[1]
                yield data

    def all(self, index_name, limit=-1, offset=0, with_doc=False, with_storage=True):
        """
        Alows to get all records for given index

        :param index_name: Index to perform the operation
        :param limit: defines limit for query
        :param offset: defines offset (how many records from start it will ignore)
        :param with_doc: if ``True`` data from **id** index will be included in output
        :param with_storage: if ``True`` data from index storage will be included, otherwise just metadata
        """
        try:
            ind = self.indexes_names[index_name]
        except KeyError:
            self.__not_opened()
            raise IndexNotFoundException(
                "Index `%s` doesn't exists" % index_name)
        storage = ind.storage
        gen = ind.all(limit, offset)
        while True:
            try:
                doc_id, unk, start, size, status = gen.next()
            except StopIteration:
                break
            else:
                if index_name == 'id':
                    if with_storage and size:
                        data = storage.get(start, size, status)
                    else:
                        data = {}
                    data['_id'] = doc_id
                    data['_rev'] = unk
                else:
                    data = {}
                    if with_storage and size:
                        data['value'] = storage.get(start, size, status)
                    data['key'] = unk
                    data['_id'] = doc_id
                    if with_doc:
                        doc = self.get('id', doc_id, False)
                        data['doc'] = doc
                yield data

    def run(self, index_name, target_funct, *args, **kwargs):
        """
        Allows to execute given function on Database side
        (important for server mode)

        If ``target_funct==sum`` then given index must have ``run_sum`` method.

        :param index_name: index name to perform action.
        :param target_funct: target function name (without *run* prefix)
        :param \*args: ``*args`` for function
        :param \*\*kwargs: ``**kwargs`` for function

        """
        try:
            ind = self.indexes_names[index_name]
        except KeyError:
            self.__not_opened()
            raise IndexNotFoundException(
                "Index `%s` doesn't exists" % index_name)
        try:
            funct = getattr(ind, "run_" + target_funct)
        except AttributeError:
            raise IndexException("Invalid function to run")
        return funct(self, *args, **kwargs)

    def count(self, target_funct, *args, **kwargs):
        """
        Counter. Allows to execute for example

        .. code-block:: python

            db.count(db.all, 'id')

        And it will return then how much records are in your ``id`` index.

        .. warning::
            It sets ``kwargs['with_storage'] = False`` and ``kwargs['with_doc'] = False``


        """
        kwargs['with_storage'] = False
        kwargs['with_doc'] = False
        iter_ = target_funct(*args, **kwargs)
        i = 0
        while True:
            try:
                iter_.next()
                i += 1
            except StopIteration:
                break
        return i

    def delete(self, data):
        """
        Delete data from database.

        ``data`` has to contain ``_id`` and ``_rev`` fields.

        :param data: data to delete
        """
        if not '_rev' in data or not '_id' in data:
            raise PreconditionsException("Can't delete without _rev or _id")
        _id = data['_id']
        _rev = data['_rev']
        try:
            _id = bytes(_id)
            _rev = bytes(_rev)
        except:
            raise PreconditionsException(
                "`_id` and `_rev` must be valid bytes object")
        data['_deleted'] = True
        self._delete_indexes(_id, _rev, data)
        return True

    def compact(self):
        """
        Compact all indexes. Runs :py:meth:`._compact_indexes` behind.
        """
        self.__not_opened()
        self._compact_indexes()

    def reindex(self):
        """
        Reindex all indexes. Runs :py:meth:`._reindex_indexes` behind.
        """
        self.__not_opened()
        self._reindex_indexes()

    def flush_indexes(self):
        """
        Flushes all indexes
        """
        self.__not_opened()
        for index in self.indexes:
            index.flush()

    def flush(self):
        """
        Flushes all indexes. Runs :py:meth:`.flush_indexes` behind.
        """
        return self.flush_indexes()

    def fsync(self):
        """
        It forces the kernel buffer to be written to disk. Use when you're sure that you need to.
        """
        self.__not_opened()
        for index in self.indexes:
            index.flush()
            index.fsync()

    def __get_size(self):
        """
        :returns: total size of database.
        """
        if not self.path:
            return 0
        return sum(
            os.path.getsize(os.path.join(dirpath, filename)) for dirpath, dirnames,
            filenames in os.walk(self.path) for filename in filenames)

    def get_index_details(self, name):
        """
        Will return index properties.

        :returns: index details
        """
        self.__not_opened()
        try:
            db_index = self.indexes_names[name]
        except KeyError:
            self.__not_opened()
            raise IndexNotFoundException("Index doesn't exist")

        props = {}
        for key, value in db_index.__dict__.iteritems():
            if not callable(value):  # not using inspect etc...
                props[key] = value

        return props

    def get_db_details(self):
        """
        Get's database details, size, indexes, environment etc.

        :returns: database details
        """
        props = {}
        props['path'] = self.path
        props['size'] = self.__get_size()
        props['indexes'] = self.indexes_names.keys()
        props['cdb_environment'] = cdb_environment
        return props

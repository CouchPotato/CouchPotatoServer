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
import struct
import shutil
import marshal
import io


try:
    from CodernityDB import __version__
except ImportError:
    from __init__ import __version__


class StorageException(Exception):
    pass


class DummyStorage(object):
    """
    Storage mostly used to fake real storage
    """

    def create(self, *args, **kwargs):
        pass

    def open(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass

    def data_from(self, *args, **kwargs):
        pass

    def data_to(self, *args, **kwargs):
        pass

    def save(self, *args, **kwargs):
        return 0, 0

    def insert(self, *args, **kwargs):
        return self.save(*args, **kwargs)

    def update(self, *args, **kwargs):
        return 0, 0

    def get(self, *args, **kwargs):
        return None

    # def compact(self, *args, **kwargs):
    #     pass

    def fsync(self, *args, **kwargs):
        pass

    def flush(self, *args, **kwargs):
        pass


class IU_Storage(object):

    __version__ = __version__

    def __init__(self, db_path, name='main'):
        self.db_path = db_path
        self.name = name
        self._header_size = 100

    def create(self):
        if os.path.exists(os.path.join(self.db_path, self.name + "_stor")):
            raise IOError("Storage already exists!")
        with io.open(os.path.join(self.db_path, self.name + "_stor"), 'wb') as f:
            f.write(struct.pack("10s90s", self.__version__, '|||||'))
            f.close()
        self._f = io.open(os.path.join(
            self.db_path, self.name + "_stor"), 'r+b', buffering=0)
        self.flush()
        self._f.seek(0, 2)

    def open(self):
        if not os.path.exists(os.path.join(self.db_path, self.name + "_stor")):
            raise IOError("Storage doesn't exists!")
        self._f = io.open(os.path.join(
            self.db_path, self.name + "_stor"), 'r+b', buffering=0)
        self.flush()
        self._f.seek(0, 2)

    def destroy(self):
        os.unlink(os.path.join(self.db_path, self.name + '_stor'))

    def close(self):
        self._f.close()
        # self.flush()
        # self.fsync()

    def data_from(self, data):
        return marshal.loads(data)

    def data_to(self, data):
        return marshal.dumps(data)

    def save(self, data):
        s_data = self.data_to(data)
        self._f.seek(0, 2)
        start = self._f.tell()
        size = len(s_data)
        self._f.write(s_data)
        self.flush()
        return start, size

    def insert(self, data):
        return self.save(data)

    def update(self, data):
        return self.save(data)

    def get(self, start, size, status='c'):
        if status == 'd':
            return None
        else:
            self._f.seek(start)
            return self.data_from(self._f.read(size))

    def flush(self):
        self._f.flush()

    def fsync(self):
        os.fsync(self._f.fileno())


# classes for public use, done in this way because of
# generation static files with indexes (_index directory)


class Storage(IU_Storage):
    pass

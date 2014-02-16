#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-----------------------
# Name: cache_file.py
# Python Library
# Author: Raymond Wagner
# Purpose: Persistant file-backed cache using /tmp/ to share data
#          using flock or msvcrt.locking to allow safe concurrent
#          access.
#-----------------------

import struct
import errno
import json
import time
import os
import io

from cStringIO import StringIO

from tmdb_exceptions import *
from cache_engine import CacheEngine, CacheObject

####################
# Cache File Format
#------------------
# cache version         (2) unsigned short
# slot count            (2) unsigned short
# slot 0: timestamp     (8) double
# slot 0: lifetime      (4) unsigned int
# slot 0: seek point    (4) unsigned int
# slot 1: timestamp
# slot 1: lifetime          index slots are IDd by their query date and
# slot 1: seek point        are filled incrementally forwards. lifetime
#   ....                    is how long after query date before the item
#   ....                    expires, and seek point is the location of the
# slot N-2: timestamp       start of data for that entry. 256 empty slots
# slot N-2: lifetime        are pre-allocated, allowing fast updates.
# slot N-2: seek point      when all slots are filled, the cache file is
# slot N-1: timestamp       rewritten from scrach to add more slots.
# slot N-1: lifetime
# slot N-1: seek point
# block 1               (?) ASCII
# block 2
#    ....                   blocks are just simple ASCII text, generated
#    ....                   as independent objects by the JSON encoder
# block N-2
# block N-1
#
####################


def _donothing(*args, **kwargs):
    pass

try:
    import fcntl
    class Flock(object):
        """
        Context manager to flock file for the duration the object
        exists. Referenced file will be automatically unflocked as the
        interpreter exits the context.
        Supports an optional callback to process the error and optionally
        suppress it.
        """
        LOCK_EX = fcntl.LOCK_EX
        LOCK_SH = fcntl.LOCK_SH

        def __init__(self, fileobj, operation, callback=None):
            self.fileobj = fileobj
            self.operation = operation
            self.callback = callback

        def __enter__(self):
            fcntl.flock(self.fileobj, self.operation)

        def __exit__(self, exc_type, exc_value, exc_tb):
            suppress = False
            if callable(self.callback):
                suppress = self.callback(exc_type, exc_value, exc_tb)
            fcntl.flock(self.fileobj, fcntl.LOCK_UN)
            return suppress

    def parse_filename(filename):
        if '$' in filename:
            # replace any environmental variables
            filename = os.path.expandvars(filename)
        if filename.startswith('~'):
            # check for home directory
            return os.path.expanduser(filename)
        elif filename.startswith('/'):
            # check for absolute path
            return filename
        # return path with temp directory prepended
        return '/tmp/' + filename

except ImportError:
    import msvcrt
    class Flock( object ):
        LOCK_EX = msvcrt.LK_LOCK
        LOCK_SH = msvcrt.LK_LOCK

        def __init__(self, fileobj, operation, callback=None):
            self.fileobj = fileobj
            self.operation = operation
            self.callback = callback

        def __enter__(self):
            self.size = os.path.getsize(self.fileobj.name)
            msvcrt.locking(self.fileobj.fileno(), self.operation, self.size)

        def __exit__(self, exc_type, exc_value, exc_tb):
            suppress = False
            if callable(self.callback):
                suppress = self.callback(exc_type, exc_value, exc_tb)
            msvcrt.locking(self.fileobj.fileno(), msvcrt.LK_UNLCK, self.size)
            return suppress

    def parse_filename(filename):
        if '%' in filename:
            # replace any environmental variables
            filename = os.path.expandvars(filename)
        if filename.startswith('~'):
            # check for home directory
            return os.path.expanduser(filename)
        elif (ord(filename[0]) in (range(65, 91) + range(99, 123))) \
                and (filename[1:3] == ':\\'):
            # check for absolute drive path (e.g. C:\...)
            return filename
        elif (filename.count('\\') >= 3) and (filename.startswith('\\\\')):
            # check for absolute UNC path (e.g. \\server\...)
            return filename
        # return path with temp directory prepended
        return os.path.expandvars(os.path.join('%TEMP%', filename))


class FileCacheObject(CacheObject):
    _struct = struct.Struct('dII')  # double and two ints
                                    # timestamp, lifetime, position

    @classmethod
    def fromFile(cls, fd):
        dat = cls._struct.unpack(fd.read(cls._struct.size))
        obj = cls(None, None, dat[1], dat[0])
        obj.position = dat[2]
        return obj

    def __init__(self, *args, **kwargs):
        self._key = None
        self._data = None
        self._size = None
        self._buff = StringIO()
        super(FileCacheObject, self).__init__(*args, **kwargs)

    @property
    def size(self):
        if self._size is None:
            self._buff.seek(0, 2)
            size = self._buff.tell()
            if size == 0:
                if (self._key is None) or (self._data is None):
                    raise RuntimeError
                json.dump([self.key, self.data], self._buff)
                self._size = self._buff.tell()
            self._size = size
        return self._size

    @size.setter
    def size(self, value):
        self._size = value

    @property
    def key(self):
        if self._key is None:
            try:
                self._key, self._data = json.loads(self._buff.getvalue())
            except:
                pass
        return self._key

    @key.setter
    def key(self, value):
        self._key = value

    @property
    def data(self):
        if self._data is None:
            self._key, self._data = json.loads(self._buff.getvalue())
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    def load(self, fd):
        fd.seek(self.position)
        self._buff.seek(0)
        self._buff.write(fd.read(self.size))

    def dumpslot(self, fd):
        pos = fd.tell()
        fd.write(self._struct.pack(self.creation, self.lifetime, self.position))

    def dumpdata(self, fd):
        self.size
        fd.seek(self.position)
        fd.write(self._buff.getvalue())


class FileEngine( CacheEngine ):
    """Simple file-backed engine."""
    name = 'file'
    _struct = struct.Struct('HH')  # two shorts for version and count
    _version = 2

    def __init__(self, parent):
        super(FileEngine, self).__init__(parent)
        self.configure(None)

    def configure(self, filename, preallocate=256):
        self.preallocate = preallocate
        self.cachefile = filename
        self.size = 0
        self.free = 0
        self.age = 0

    def _init_cache(self):
        # only run this once
        self._init_cache = _donothing

        if self.cachefile is None:
            raise TMDBCacheError("No cache filename given.")
        self.cachefile = parse_filename(self.cachefile)

        try:
            # attempt to read existing cache at filename
            # handle any errors that occur
            self._open('r+b')
            # seems to have read fine, make sure we have write access
            if not os.access(self.cachefile, os.W_OK):
                raise TMDBCacheWriteError(self.cachefile)

        except IOError as e:
            if e.errno == errno.ENOENT:
                # file does not exist, create a new one
                try:
                    self._open('w+b')
                    self._write([])
                except IOError as e:
                    if e.errno == errno.ENOENT:
                        # directory does not exist
                        raise TMDBCacheDirectoryError(self.cachefile)
                    elif e.errno == errno.EACCES:
                        # user does not have rights to create new file
                        raise TMDBCacheWriteError(self.cachefile)
                    else:
                        # let the unhandled error continue through
                        raise
            elif e.errno == errno.EACCES:
                # file exists, but we do not have permission to access it
                raise TMDBCacheReadError(self.cachefile)
            else:
                # let the unhandled error continue through
                raise

    def get(self, date):
        self._init_cache()
        self._open('r+b')
        
        with Flock(self.cachefd, Flock.LOCK_SH):
            # return any new objects in the cache
            return self._read(date)

    def put(self, key, value, lifetime):
        self._init_cache()
        self._open('r+b')

        with Flock(self.cachefd, Flock.LOCK_EX):
            newobjs = self._read(self.age)
            newobjs.append(FileCacheObject(key, value, lifetime))

            # this will cause a new file object to be opened with the proper
            # access mode, however the Flock should keep the old object open
            # and properly locked
            self._open('r+b')
            self._write(newobjs)
            return newobjs

    def _open(self, mode='r+b'):
        # enforce binary operation
        try:
            if self.cachefd.mode == mode:
                # already opened in requested mode, nothing to do
                self.cachefd.seek(0)
                return
        except:
            pass  # catch issue of no cachefile yet opened
        self.cachefd = io.open(self.cachefile, mode)

    def _read(self, date):
        try:
            self.cachefd.seek(0)
            version, count = self._struct.unpack(\
                                    self.cachefd.read(self._struct.size))
            if version != self._version:
                # old version, break out and well rewrite when finished
                raise Exception

            self.size = count
            cache = []
            while count:
                # loop through storage definitions
                obj = FileCacheObject.fromFile(self.cachefd)
                cache.append(obj)
                count -= 1

        except:
            # failed to read information, so just discard it and return empty
            self.size = 0
            self.free = 0
            return []

        # get end of file
        self.cachefd.seek(0, 2)
        position = self.cachefd.tell()
        newobjs = []
        emptycount = 0

        # walk backward through all, collecting new content and populating size
        while len(cache):
            obj = cache.pop()
            if obj.creation == 0:
                # unused slot, skip
                emptycount += 1
            elif obj.expired:
                # object has passed expiration date, no sense processing
                continue
            elif obj.creation > date:
                # used slot with new data, process
                obj.size, position = position - obj.position, obj.position
                newobjs.append(obj)
                # update age
                self.age = max(self.age, obj.creation)
            elif len(newobjs):
                # end of new data, break
                break

        # walk forward and load new content
        for obj in newobjs:
            obj.load(self.cachefd)

        self.free = emptycount
        return newobjs

    def _write(self, data):
        if self.free and (self.size != self.free):
            # we only care about the last data point, since the rest are
            # already stored in the file
            data = data[-1]

            # determine write position of data in cache
            self.cachefd.seek(0, 2)
            end = self.cachefd.tell()
            data.position = end

            # write incremental update to free slot
            self.cachefd.seek(4 + 16*(self.size-self.free))
            data.dumpslot(self.cachefd)
            data.dumpdata(self.cachefd)

        else:
            # rewrite cache file from scratch
            # pull data from parent cache
            data.extend(self.parent()._data.values())
            data.sort(key=lambda x: x.creation)
            # write header
            size = len(data) + self.preallocate
            self.cachefd.seek(0)
            self.cachefd.truncate()
            self.cachefd.write(self._struct.pack(self._version, size))
            # write storage slot definitions
            prev = None
            for d in data:
                if prev == None:
                    d.position = 4 + 16*size
                else:
                    d.position = prev.position + prev.size
                d.dumpslot(self.cachefd)
                prev = d
            # fill in allocated slots
            for i in range(2**8):
                self.cachefd.write(FileCacheObject._struct.pack(0, 0, 0))
            # write stored data
            for d in data:
                d.dumpdata(self.cachefd)

        self.cachefd.flush()

    def expire(self, key):
        pass

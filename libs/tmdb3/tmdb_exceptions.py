#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-----------------------
# Name: tmdb_exceptions.py    Common exceptions used in tmdbv3 API library
# Python Library
# Author: Raymond Wagner
#-----------------------


class TMDBError(Exception):
    Error = 0
    KeyError = 10
    KeyMissing = 20
    KeyInvalid = 30
    KeyRevoked = 40
    RequestError = 50
    RequestInvalid = 51
    PagingIssue = 60
    CacheError = 70
    CacheReadError = 71
    CacheWriteError = 72
    CacheDirectoryError = 73
    ImageSizeError = 80
    HTTPError = 90
    Offline = 100
    LocaleError = 110

    def __init__(self, msg=None, errno=0):
        self.errno = errno
        if errno == 0:
            self.errno = getattr(self, 'TMDB'+self.__class__.__name__, errno)
        self.args = (msg,)


class TMDBKeyError(TMDBError):
    pass


class TMDBKeyMissing(TMDBKeyError):
    pass


class TMDBKeyInvalid(TMDBKeyError):
    pass


class TMDBKeyRevoked(TMDBKeyInvalid):
    pass


class TMDBRequestError(TMDBError):
    pass


class TMDBRequestInvalid(TMDBRequestError):
    pass


class TMDBPagingIssue(TMDBRequestError):
    pass


class TMDBCacheError(TMDBRequestError):
    pass


class TMDBCacheReadError(TMDBCacheError):
    def __init__(self, filename):
        super(TMDBCacheReadError, self).__init__(
            "User does not have permission to access cache file: {0}."\
                .format(filename))
        self.filename = filename


class TMDBCacheWriteError(TMDBCacheError):
    def __init__(self, filename):
        super(TMDBCacheWriteError, self).__init__(
            "User does not have permission to write cache file: {0}."\
                .format(filename))
        self.filename = filename


class TMDBCacheDirectoryError(TMDBCacheError):
    def __init__(self, filename):
        super(TMDBCacheDirectoryError, self).__init__(
            "Directory containing cache file does not exist: {0}."\
                .format(filename))
        self.filename = filename


class TMDBImageSizeError(TMDBError ):
    pass


class TMDBHTTPError(TMDBError):
    def __init__(self, err):
        self.httperrno = err.code
        self.response = err.fp.read()
        super(TMDBHTTPError, self).__init__(str(err))


class TMDBOffline(TMDBError):
    pass


class TMDBLocaleError(TMDBError):
    pass

#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:unlicense (http://unlicense.org/)

"""
urllib2 caching handler
Modified from http://code.activestate.com/recipes/491261/
"""
from __future__ import with_statement

__author__ = "dbr/Ben"
__version__ = "1.8.2"

import os
import time
import errno
import httplib
import urllib2
import StringIO
from hashlib import md5
from threading import RLock

cache_lock = RLock()

def locked_function(origfunc):
    """Decorator to execute function under lock"""
    def wrapped(*args, **kwargs):
        cache_lock.acquire()
        try:
            return origfunc(*args, **kwargs)
        finally:
            cache_lock.release()
    return wrapped

def calculate_cache_path(cache_location, url):
    """Checks if [cache_location]/[hash_of_url].headers and .body exist
    """
    thumb = md5(url).hexdigest()
    header = os.path.join(cache_location, thumb + ".headers")
    body = os.path.join(cache_location, thumb + ".body")
    return header, body

def check_cache_time(path, max_age):
    """Checks if a file has been created/modified in the [last max_age] seconds.
    False means the file is too old (or doesn't exist), True means it is
    up-to-date and valid"""
    if not os.path.isfile(path):
        return False
    cache_modified_time = os.stat(path).st_mtime
    time_now = time.time()
    if cache_modified_time < time_now - max_age:
        # Cache is old
        return False
    else:
        return True

@locked_function
def exists_in_cache(cache_location, url, max_age):
    """Returns if header AND body cache file exist (and are up-to-date)"""
    hpath, bpath = calculate_cache_path(cache_location, url)
    if os.path.exists(hpath) and os.path.exists(bpath):
        return(
            check_cache_time(hpath, max_age)
            and check_cache_time(bpath, max_age)
        )
    else:
        # File does not exist
        return False

@locked_function
def store_in_cache(cache_location, url, response):
    """Tries to store response in cache."""
    hpath, bpath = calculate_cache_path(cache_location, url)
    try:
        outf = open(hpath, "wb")
        headers = str(response.info())
        outf.write(headers)
        outf.close()

        outf = open(bpath, "wb")
        outf.write(response.read())
        outf.close()
    except IOError:
        return True
    else:
        return False
        
@locked_function
def delete_from_cache(cache_location, url):
    """Deletes a response in cache."""
    hpath, bpath = calculate_cache_path(cache_location, url)
    try:
        if os.path.exists(hpath):
            os.remove(hpath)
        if os.path.exists(bpath):
            os.remove(bpath)
    except IOError:
        return True
    else:
        return False

class CacheHandler(urllib2.BaseHandler):
    """Stores responses in a persistant on-disk cache.

    If a subsequent GET request is made for the same URL, the stored
    response is returned, saving time, resources and bandwidth
    """
    @locked_function
    def __init__(self, cache_location, max_age = 21600):
        """The location of the cache directory"""
        self.max_age = max_age
        self.cache_location = cache_location
        if not os.path.exists(self.cache_location):
            try:
                os.mkdir(self.cache_location)
            except OSError, e:
                if e.errno == errno.EEXIST and os.path.isdir(self.cache_location):
                    # File exists, and it's a directory,
                    # another process beat us to creating this dir, that's OK.
                    pass
                else:
                    # Our target dir is already a file, or different error,
                    # relay the error!
                    raise

    def default_open(self, request):
        """Handles GET requests, if the response is cached it returns it
        """
        if request.get_method() is not "GET":
            return None # let the next handler try to handle the request

        if exists_in_cache(
            self.cache_location, request.get_full_url(), self.max_age
        ):
            return CachedResponse(
                self.cache_location,
                request.get_full_url(),
                set_cache_header = True
            )
        else:
            return None

    def http_response(self, request, response):
        """Gets a HTTP response, if it was a GET request and the status code
        starts with 2 (200 OK etc) it caches it and returns a CachedResponse
        """
        if (request.get_method() == "GET"
            and str(response.code).startswith("2")
        ):
            if 'x-local-cache' not in response.info():
                # Response is not cached
                set_cache_header = store_in_cache(
                    self.cache_location,
                    request.get_full_url(),
                    response
                )
            else:
                set_cache_header = True

            return CachedResponse(
                self.cache_location,
                request.get_full_url(),
                set_cache_header = set_cache_header
            )
        else:
            return response

class CachedResponse(StringIO.StringIO):
    """An urllib2.response-like object for cached responses.

    To determine if a response is cached or coming directly from
    the network, check the x-local-cache header rather than the object type.
    """

    @locked_function
    def __init__(self, cache_location, url, set_cache_header=True):
        self.cache_location = cache_location
        hpath, bpath = calculate_cache_path(cache_location, url)

        StringIO.StringIO.__init__(self, file(bpath, "rb").read())

        self.url     = url
        self.code    = 200
        self.msg     = "OK"
        headerbuf = file(hpath, "rb").read()
        if set_cache_header:
            headerbuf += "x-local-cache: %s\r\n" % (bpath)
        self.headers = httplib.HTTPMessage(StringIO.StringIO(headerbuf))

    def info(self):
        """Returns headers
        """
        return self.headers

    def geturl(self):
        """Returns original URL
        """
        return self.url

    @locked_function
    def recache(self):
        new_request = urllib2.urlopen(self.url)
        set_cache_header = store_in_cache(
            self.cache_location,
            new_request.url,
            new_request
        )
        CachedResponse.__init__(self, self.cache_location, self.url, True)

    @locked_function
    def delete_cache(self):
        delete_from_cache(
            self.cache_location,
            self.url
        )
    

if __name__ == "__main__":
    def main():
        """Quick test/example of CacheHandler"""
        opener = urllib2.build_opener(CacheHandler("/tmp/"))
        response = opener.open("http://google.com")
        print response.headers
        print "Response:", response.read()

        response.recache()
        print response.headers
        print "After recache:", response.read()

        # Test usage in threads
        from threading import Thread
        class CacheThreadTest(Thread):
            lastdata = None
            def run(self):
                req = opener.open("http://google.com")
                newdata = req.read()
                if self.lastdata is None:
                    self.lastdata = newdata
                assert self.lastdata == newdata, "Data was not consistent, uhoh"
                req.recache()
        threads = [CacheThreadTest() for x in range(50)]
        print "Starting threads"
        [t.start() for t in threads]
        print "..done"
        print "Joining threads"
        [t.join() for t in threads]
        print "..done"
    main()

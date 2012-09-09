#  Copyright (c) 2002-2010 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

"""
Futz with files like a pro.
"""

import errno, exceptions, os, stat, tempfile

try:
    import bsddb
except ImportError:
    DBNoSuchFileError = None
else:
    DBNoSuchFileError = bsddb.db.DBNoSuchFileError

# read_file() and write_file() copied from Mark Seaborn's blog post.  Please
# read it for complete rationale:
# http://lackingrhoticity.blogspot.com/2009/12/readfile-and-writefile-in-python.html

def read_file(filename, mode='rb'):
    """ Read the contents of the file named filename and return it in
    a string. This function closes the file handle before it returns
    (even if the underlying Python implementation's garbage collector
    doesn't). """
    fh = open(filename, mode)
    try:
        return fh.read()
    finally:
        fh.close()

def write_file(filename, data, mode='wb'):
    """ Write the string data into a file named filename. This
    function closes the file handle (ensuring that the written data is
    flushed from the perspective of the Python implementation) before
    it returns (even if the underlying Python implementation's garbage
    collector doesn't)."""
    fh = open(filename, mode)
    try:
        fh.write(data)
    finally:
        fh.close()

# For backwards-compatibility in case someone is using these names. We used to
# have a superkludge in fileutil.py under these names.
def rename(src, dst, tries=4, basedelay=0.1):
    return os.rename(src, dst)

def remove(f, tries=4, basedelay=0.1):
    return os.remove(f)

def rmdir(f, tries=4, basedelay=0.1):
    return os.rmdir(f)

class _Dir(object):
    """
    Hold a set of files and subdirs and clean them all up when asked to.
    """
    def __init__(self, name, cleanup=True):
        self.name = name
        self.cleanup = cleanup
        self.files = []
        self.subdirs = set()

    def file(self, fname, mode=None):
        """
        Create a file in the tempdir and remember it so as to close() it
        before attempting to cleanup the temp dir.

        @rtype: file
        """
        ffn = os.path.join(self.name, fname)
        if mode is not None:
            fo = open(ffn, mode)
        else:
            fo = open(ffn)
        self.register_file(fo)
        return fo

    def subdir(self, dirname):
        """
        Create a subdirectory in the tempdir and remember it so as to call
        shutdown() on it before attempting to clean up.

        @rtype: _Dir instance
        """
        ffn = os.path.join(self.name, dirname)
        sd = _Dir(ffn, self.cleanup)
        self.register_subdir(sd)
        make_dirs(sd.name)
        return sd

    def register_file(self, fileobj):
        """
        Remember the file object and call close() on it before attempting to
        clean up.
        """
        self.files.append(fileobj)

    def register_subdir(self, dirobj):
        """
        Remember the _Dir object and call shutdown() on it before attempting
        to clean up.
        """
        self.subdirs.add(dirobj)

    def shutdown(self):
        if self.cleanup:
            for subdir in hasattr(self, 'subdirs') and self.subdirs or []:
                subdir.shutdown()
            for fileobj in hasattr(self, 'files') and self.files or []:
                if DBNoSuchFileError is None:
                    fileobj.close() # "close()" is idempotent so we don't need to catch exceptions here
                else:
                    try:
                        fileobj.close()
                    except DBNoSuchFileError:
                        # Ah, except that the bsddb module's file-like object (a DB object) has a non-idempotent close...
                        pass

            if hasattr(self, 'name'):
                rm_dir(self.name)

    def __repr__(self):
        return "<%s instance at %x %s>" % (self.__class__.__name__, id(self), self.name)

    def __str__(self):
        return self.__repr__()

    def __del__(self):
        try:
            self.shutdown()
        except:
            import traceback
            traceback.print_exc()

class NamedTemporaryDirectory(_Dir):
    """
    Call tempfile.mkdtemp(), store the name of the dir in self.name, and
    rm_dir() when it gets garbage collected or "shutdown()".

    Also keep track of file objects for files within the tempdir and call
    close() on them before rm_dir().  This is a convenient way to open temp
    files within the directory, and it is very helpful on Windows because you
    can't delete a directory which contains a file which is currently open.
    """

    def __init__(self, cleanup=True, *args, **kwargs):
        """ If cleanup, then the directory will be rmrf'ed when the object is shutdown. """
        name = tempfile.mkdtemp(*args, **kwargs)
        _Dir.__init__(self, name, cleanup)

class ReopenableNamedTemporaryFile:
    """
    This uses tempfile.mkstemp() to generate a secure temp file.  It then closes
    the file, leaving a zero-length file as a placeholder.  You can get the
    filename with ReopenableNamedTemporaryFile.name.  When the
    ReopenableNamedTemporaryFile instance is garbage collected or its shutdown()
    method is called, it deletes the file.
    """
    def __init__(self, *args, **kwargs):
        fd, self.name = tempfile.mkstemp(*args, **kwargs)
        os.close(fd)

    def __repr__(self):
        return "<%s instance at %x %s>" % (self.__class__.__name__, id(self), self.name)

    def __str__(self):
        return self.__repr__()

    def __del__(self):
        self.shutdown()

    def shutdown(self):
        remove(self.name)

def make_dirs(dirname, mode=0777):
    """
    An idempotent version of os.makedirs().  If the dir already exists, do
    nothing and return without raising an exception.  If this call creates the
    dir, return without raising an exception.  If there is an error that
    prevents creation or if the directory gets deleted after make_dirs() creates
    it and before make_dirs() checks that it exists, raise an exception.
    """
    tx = None
    try:
        os.makedirs(dirname, mode)
    except OSError, x:
        tx = x

    if not os.path.isdir(dirname):
        if tx:
            raise tx
        raise exceptions.IOError, "unknown error prevented creation of directory, or deleted the directory immediately after creation: %s" % dirname # careful not to construct an IOError with a 2-tuple, as that has a special meaning...

def rmtree(dirname):
    """
    A threadsafe and idempotent version of shutil.rmtree().  If the dir is
    already gone, do nothing and return without raising an exception.  If this
    call removes the dir, return without raising an exception.  If there is an
    error that prevents deletion or if the directory gets created again after
    rm_dir() deletes it and before rm_dir() checks that it is gone, raise an
    exception.
    """
    excs = []
    try:
        os.chmod(dirname, stat.S_IWRITE | stat.S_IEXEC | stat.S_IREAD)
        for f in os.listdir(dirname):
            fullname = os.path.join(dirname, f)
            if os.path.isdir(fullname):
                rm_dir(fullname)
            else:
                remove(fullname)
        os.rmdir(dirname)
    except EnvironmentError, le:
        # Ignore "No such file or directory", collect any other exception.
        if (le.args[0] != 2 and le.args[0] != 3) or (le.args[0] != errno.ENOENT):
            excs.append(le)
    except Exception, le:
        excs.append(le)

    # Okay, now we've recursively removed everything, ignoring any "No
    # such file or directory" errors, and collecting any other errors.

    if os.path.exists(dirname):
        if len(excs) == 1:
            raise excs[0]
        if len(excs) == 0:
            raise OSError, "Failed to remove dir for unknown reason."
        raise OSError, excs

def rm_dir(dirname):
    # Renamed to be like shutil.rmtree and unlike rmdir.
    return rmtree(dirname)

def remove_if_possible(f):
    try:
        remove(f)
    except EnvironmentError:
        pass

def remove_if_present(f):
    try:
        remove(f)
    except EnvironmentError, le:
        # Ignore "No such file or directory", re-raise any other exception.
        if (le.args[0] != 2 and le.args[0] != 3) or (le.args[0] != errno.ENOENT):
            raise

def rmdir_if_possible(f):
    try:
        rmdir(f)
    except EnvironmentError:
        pass

def open_or_create(fname, binarymode=True):
    try:
        f = open(fname, binarymode and "r+b" or "r+")
    except EnvironmentError:
        f = open(fname, binarymode and "w+b" or "w+")
    return f

def du(basedir):
    size = 0

    for root, dirs, files in os.walk(basedir):
        for f in files:
            fn = os.path.join(root, f)
            size += os.path.getsize(fn)

    return size

import unittest

import os

from pyutil import fileutil

class FileUtil(unittest.TestCase):
    def mkdir(self, basedir, path, mode=0777):
        fn = os.path.join(basedir, path)
        fileutil.make_dirs(fn, mode)

    def touch(self, basedir, path, mode=None, data="touch\n"):
        fn = os.path.join(basedir, path)
        f = open(fn, "w")
        f.write(data)
        f.close()
        if mode is not None:
            os.chmod(fn, mode)

    def test_du(self):
        basedir = "util/FileUtil/test_du"
        fileutil.make_dirs(basedir)
        d = os.path.join(basedir, "space-consuming")
        self.mkdir(d, "a/b")
        self.touch(d, "a/b/1.txt", data="a"*10)
        self.touch(d, "a/b/2.txt", data="b"*11)
        self.mkdir(d, "a/c")
        self.touch(d, "a/c/1.txt", data="c"*12)
        self.touch(d, "a/c/2.txt", data="d"*13)

        used = fileutil.du(basedir)
        self.failUnlessEqual(10+11+12+13, used)


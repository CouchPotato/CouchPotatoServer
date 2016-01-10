import os
import sys


class SoftChroot:
    def __init__(self, chdir):
        self.enabled = False

        self.chdir = chdir

        if None != self.chdir:
            self.chdir = self.chdir.strip()
            self.chdir = self.chdir.rstrip(os.path.sep) + os.path.sep
            self.enabled = True

    def is_root_abs(self, abspath):
        if not self.enabled:
            raise Exception('chroot disabled')
        if None == abspath:
            return False
            
        path = abspath.rstrip(os.path.sep) + os.path.sep
        return self.chdir == path

    def is_subdir(self, path):
        if not self.enabled:
            return True

        if None == path:
            return False

        if not path.endswith(os.path.sep):
            path += os.path.sep

        return path.startswith(self.chdir)

    def add(self, path):
        if not self.enabled:
            return path

        if None == path or len(path)==0:
            return self.chdir

        if not path.startswith(os.path.sep):
            raise ValueError("path must starts with '/'")

        return self.chdir[:-1] + path

    def cut(self, path):
        if not self.enabled:
            return path

        if None == path or 0==len(path):
            raise ValueError('path is empty')

        if path == self.chdir.rstrip(os.path.sep):
            return '/'

        if not path.startswith(self.chdir):
            raise ValueError("path must starts with 'chdir'")

        l = len(self.chdir)-1

        return path[l:]

import os
import sys


class SoftChrootInitError(IOError):
    """Error during soft-chroot initialization"""
    pass

class SoftChroot:
    """Soft Chroot module

    Provides chroot feature for interation with Web-UI. Since it is not real chroot, so the name is SOFT CHROOT.
    The module prevents access to entire file-system, allowing access only to subdirs of SOFT-CHROOT directory.
    """
    def __init__(self):
        self.enabled = None
        self.chdir = None

    def initialize(self, chdir):
        """ initialize module, by setting soft-chroot-directory

        Sets soft-chroot directory and 'enabled'-flag

        Args:
            self (SoftChroot) : self
            chdir (string) : absolute path to soft-chroot

        Raises:
            SoftChrootInitError: when chdir doesn't exist
        """

        orig_chdir = chdir

        if chdir:
            chdir = chdir.strip()

        if (chdir):
            # enabling soft-chroot:
            if not os.path.isdir(chdir):
                raise SoftChrootInitError(2, 'SOFT-CHROOT is requested, but the folder doesn\'t exist', orig_chdir)
            
            self.enabled = True
            self.chdir = chdir.rstrip(os.path.sep) + os.path.sep
        else:
            self.enabled = False

    def get_chroot(self):
        """Returns root in chrooted environment

        Raises:
            RuntimeError: when `SoftChroot` is not initialized OR enabled
        """
        if None == self.enabled:
            raise RuntimeError('SoftChroot is not initialized')
        if not self.enabled:
            raise RuntimeError('SoftChroot is not enabled')

        return self.chdir

    def is_root_abs(self, abspath):
        """ Checks whether absolute path @abspath is the root in the soft-chrooted environment"""
        if None == self.enabled:
            raise RuntimeError('SoftChroot is not initialized')

        if None == abspath:
            raise ValueError('abspath can not be None')

        if not self.enabled:
            # if not chroot environment : check, whether parent is the same dir:
            parent = os.path.dirname(abspath.rstrip(os.path.sep))
            return parent==abspath

        # in soft-chrooted env: check, that path == chroot
        path = abspath.rstrip(os.path.sep) + os.path.sep
        return self.chdir == path

    def is_subdir(self, abspath):
        """ Checks whether @abspath is subdir (on any level) of soft-chroot"""
        if None == self.enabled:
            raise RuntimeError('SoftChroot is not initialized')

        if None == abspath:
            return False

        if not self.enabled:
            return True

        if not abspath.endswith(os.path.sep):
            abspath += os.path.sep

        return abspath.startswith(self.chdir)

    def chroot2abs(self, path):
        """ Converts chrooted path to absolute path"""

        if None == self.enabled:
            raise RuntimeError('SoftChroot is not initialized')
        if not self.enabled:
            return path

        if None == path or len(path)==0:
            return self.chdir

        if not path.startswith(os.path.sep):
            path = os.path.sep + path

        return self.chdir[:-1] + path

    def abs2chroot(self, path, force = False):
        """ Converts absolute path to chrooted path"""

        if None == self.enabled:
            raise RuntimeError('SoftChroot is not initialized')

        if None == path:
            raise ValueError('path is empty')

        if not self.enabled:
            return path

        if path == self.chdir.rstrip(os.path.sep):
            return '/'

        resulst = None
        if not path.startswith(self.chdir):
            if (force):
                result = self.get_chroot()
            else:
                raise ValueError("path must starts with 'chdir': %s" % path)
        else:
            l = len(self.chdir)-1
            result = path[l:]

        return result

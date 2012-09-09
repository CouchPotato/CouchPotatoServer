
# This is the version of this tree, as created by setup.py darcsver from the darcs patch
# information: the main version number is taken from the most recent release
# tag. If some patches have been added since the last release, this will have a
# -NN "build number" suffix, or else a -rNN "revision number" suffix. Please see
# pyutil.version_class for a description of what the different fields mean.

__pkgname__ = "pyutil"
verstr = "1.9.3"
try:
    from pyutil.version_class import Version as pyutil_Version
    __version__ = pyutil_Version(verstr)
except (ImportError, ValueError):
    # Maybe there is no pyutil installed, or this may be an older version of
    # pyutil.version_class which does not support SVN-alike revision numbers.
    from distutils.version import LooseVersion as distutils_Version
    __version__ = distutils_Version(verstr)

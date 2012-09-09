"""
Library of useful Python functions and classes.

Projects that have contributed substantial portions to pyutil:
U{Mojo Nation<http://mojonation.net/>}
U{Mnet<http://sf.net/projects/mnet>}
U{Allmydata<http://allmydata.com/>}
U{Tahoe-LAFS<http://tahoe-lafs.org/>}

mailto:zooko@zooko.com

pyutil web site: U{http://tahoe-lafs.org/trac/pyutil}
"""

__version__ = "unknown"
try:
    from _version import __version__
except ImportError:
    # We're running in a tree that hasn't run "./setup.py darcsver", and didn't
    # come with a _version.py, so we don't know what our version is. This should
    # not happen very often.
    pass
__version__ # hush pyflakes

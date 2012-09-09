# Copyright (c) 2002-2010 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

import warnings
import os, random

try:
    import hashexpand
    class SHA256Random(hashexpand.SHA256Expander, random.Random):
        def __init__(self, seed=None, deterministic=True):
            warnings.warn("deprecated", DeprecationWarning)
            if not deterministic:
                raise NotImplementedError, "SHA256Expander is always deterministic.  For non-deterministic, try urandomRandom."

            hashexpand.SHA256Expander.__init__(self)
            random.Random.__init__(self, seed)
            self.seed(seed)

        def seed(self, seed=None):
            if seed is None:
                import increasing_timer
                seed = repr(increasing_timer.time())
            hashexpand.SHA256Expander.seed(self, seed)


    class SHA256Random(hashexpand.SHA256Expander, random.Random):
        def __init__(self, seed=""):
            warnings.warn("deprecated", DeprecationWarning)
            hashexpand.SHA256Expander.__init__(self)
            self.seed(seed)

        def seed(self, seed=None):
            if seed is None:
                seed = os.urandom(32)
            hashexpand.SHA256Expander.seed(self, seed)
except ImportError, le:
    class InsecureSHA256Random:
        def __init__(self, seed=None):
            raise ImportError, le
    class SHA256Random:
        def __init__(self, seed=""):
            raise ImportError, le

class devrandomRandom(random.Random):
    """ The problem with using this one, of course, is that it blocks.  This
    is, of course, a security flaw.  (On Linux and probably on other
    systems.) --Zooko 2005-03-04

    Not repeatable.
    """
    def __init__(self):
        warnings.warn("deprecated", DeprecationWarning)
        self.dr = open("/dev/random", "r")

    def get(self, bytes):
        return self.dr.read(bytes)


class devurandomRandom(random.Random):
    """ The problem with using this one is that it gives answers even when it
    has never been properly seeded, e.g. when you are booting from CD and have
    just started up and haven't yet gathered enough entropy to actually be
    unguessable.  (On Linux and probably on other systems.)  --Zooko 2005-03-04

    Not repeatable.
    """
    def get(self, bytes):
        warnings.warn("deprecated", DeprecationWarning)
        return os.urandom(bytes)


randobj = devurandomRandom()
get = randobj.get
random = randobj.random
randrange = randobj.randrange
shuffle = randobj.shuffle
choice = randobj.choice
seed = randobj.seed

def randstr(n):
    return ''.join(map(chr, map(randrange, [0]*n, [256]*n)))

import random as insecurerandom
def insecurerandstr(n):
    return ''.join(map(chr, map(insecurerandom.randrange, [0]*n, [256]*n)))

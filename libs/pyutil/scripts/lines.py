#!/usr/bin/env python

# Copyright (c) 2005-2010 Zooko Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

from pyutil import lineutil

import sys

def main():
    if len(sys.argv) > 1 and "-s" in sys.argv[1:]:
        strip = True
        sys.argv.remove("-s")
    else:
        strip = False

    if len(sys.argv) > 1 and "-n" in sys.argv[1:]:
        nobak = True
        sys.argv.remove("-n")
    else:
        nobak = False

    if len(sys.argv) > 1:
        pipe = False
    else:
        pipe = True

    if pipe:
        lineutil.lineify_fileobjs(sys.stdin, sys.stdout)
    else:
        for fn in sys.argv[1:]:
            lineutil.lineify_file(fn, strip, nobak)

if __name__ == '__main__':
    main()


#!/usr/bin/env python

import os, sys

import zbase32

def main():
    if len(sys.argv) > 1:
        l = int(sys.argv[1])
    else:
        l = 64

    bl = (l + 7) / 8

    s = zbase32.b2a_l(os.urandom(bl), l)

    # insert some hyphens for easier memorization
    chs = 3 + (len(s)%8==0)
    i = chs
    while i < len(s)-1:
        s = s[:i] + "-" + s[i:]
        i += 1
        chs = 7-chs
        i += chs

    print s

if __name__ == '__main__':
    main()


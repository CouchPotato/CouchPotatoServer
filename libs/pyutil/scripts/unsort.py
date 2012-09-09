#!/usr/bin/env python

# randomize the lines of stdin or a file

import random, sys

def main():
    if len(sys.argv) > 1:
        fname = sys.argv[1]
        inf = open(fname, 'r')
    else:
        inf = sys.stdin

    lines = inf.readlines()
    random.shuffle(lines)
    sys.stdout.writelines(lines)

if __name__ == '__main__':
    main()

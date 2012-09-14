#!/usr/bin/env python

# output all but the first N lines of a file

# Allen Short and Jp Calderone wrote this coool version:
import itertools, sys

def main():
    K = int(sys.argv[1])
    if len(sys.argv) > 2:
        fname = sys.argv[2]
        inf = open(fname, 'r')
    else:
        inf = sys.stdin

    sys.stdout.writelines(itertools.islice(inf, K, None))

if __name__ == '__main__':
    main()

# thus replacing my dumb version:
# # from the Python Standard Library
# import sys
# 
# i = K
# for l in sys.stdin.readlines():
#     if i:
#         i -= 1
#     else:
#         print l,

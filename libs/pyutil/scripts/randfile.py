#!/usr/bin/env python

import os, sys

from random import randrange

import argparse

def main():
    CHUNKSIZE=2**20

    parser = argparse.ArgumentParser(prog="randfile", description="Create a file of pseudorandom bytes (not cryptographically secure).")

    parser.add_argument('-b', '--num-bytes', help="how many bytes to write per output file (default 20)", type=int, metavar="BYTES", default=20)
    parser.add_argument('-f', '--output-file-prefix', help="prefix of the name of the output file to create and fill with random bytes (default \"randfile\"", metavar="OUTFILEPRE", default="randfile")
    parser.add_argument('-n', '--num-files', help="how many files to write (default 1)", type=int, metavar="FILES", default=1)
    parser.add_argument('-F', '--force', help='overwrite any file already present', action='store_true')
    parser.add_argument('-p', '--progress', help='write an "x" for every file completed and a "." for every %d bytes' % CHUNKSIZE, action='store_true')
    args = parser.parse_args()
                     
    for i in xrange(args.num_files):
        bytesleft = args.num_bytes
        outputfname = args.output_file_prefix + "." + str(i)

        if args.force:
            f = open(outputfname, "wb")
        else:
            flags = os.O_WRONLY|os.O_CREAT|os.O_EXCL | (hasattr(os, 'O_BINARY') and os.O_BINARY)
            fd = os.open(outputfname, flags)
            f = os.fdopen(fd, "wb")
        zs = [0]*CHUNKSIZE
        ts = [256]*CHUNKSIZE
        while bytesleft >= CHUNKSIZE:
            f.write(''.join(map(chr, map(randrange, zs, ts))))
            bytesleft -= CHUNKSIZE

            if args.progress:
                sys.stdout.write(".") ; sys.stdout.flush()

        zs = [0]*bytesleft
        ts = [256]*bytesleft
        f.write(''.join(map(chr, map(randrange, zs, ts))))

        if args.progress:
            sys.stdout.write("x") ; sys.stdout.flush()

if __name__ == "__main__":
    main()

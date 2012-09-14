#!/usr/bin/env python

import binascii, codecs, encodings, locale, os, sys, zlib

import argparse

def listcodecs(dir):
    names = []
    for filename in os.listdir(dir):
        if filename[-3:] != '.py':
            continue
        name = filename[:-3]
        # Check whether we've found a true codec
        try:
            codecs.lookup(name)
        except LookupError:
            # Codec not found
            continue
        except Exception:
            # Probably an error from importing the codec; still it's
            # a valid code name
            pass
        names.append(name)
    return names

def listem():
    return listcodecs(encodings.__path__[0])

def _canonical_encoding(encoding):
    if encoding is None:
        encoding = 'utf-8'
    encoding = encoding.lower()
    if encoding == "cp65001":
        encoding = 'utf-8'
    elif encoding == "us-ascii" or encoding == "646":
        encoding = 'ascii'

    # sometimes Python returns an encoding name that it doesn't support for conversion
    # fail early if this happens
    try:
        u"test".encode(encoding)
    except (LookupError, AttributeError):
        raise AssertionError("The character encoding '%s' is not supported for conversion." % (encoding,))

    return encoding

def get_output_encoding():
    return _canonical_encoding(sys.stdout.encoding or locale.getpreferredencoding())

def get_argv_encoding():
    if sys.platform == 'win32':
        # Unicode arguments are not supported on Windows yet; see Tahoe-LAFS tickets #565 and #1074.
        return 'ascii'
    else:
        return get_output_encoding()

output_encoding = get_output_encoding()
argv_encoding = get_argv_encoding()

def type_unicode(argstr):
    return argstr.decode(argv_encoding)

def main():
    parser = argparse.ArgumentParser(prog="try_decoding", description="Try decoding some bytes with all sorts of different codecs and print out any that decode.")

    parser.add_argument('inputfile', help='file to decode or "-" for stdin', type=argparse.FileType('rb'), metavar='INF')
    parser.add_argument('-t', '--target', help='unicode string to match against (if any)', type=type_unicode, metavar='T')
    parser.add_argument('-a', '--accept-bytes', help='include codecs which return bytes instead of returning unicode (they will be marked with "!!!" in the output)', action='store_true')

    args = parser.parse_args()

    inb = args.inputfile.read()

    for codec in listem():
        try:
            u = inb.decode(codec)
        except (UnicodeDecodeError, IOError, TypeError, IndexError, UnicodeError, ValueError, zlib.error, binascii.Error):
            pass
        else:
            if isinstance(u, unicode):
                if args.target:
                    if args.target != u:
                        continue
                print "%19s" % codec,
                print ':',
                print u.encode(output_encoding)
            else:
                if not args.accept_bytes:
                    continue
                print "%19s" % codec,
                print "!!! ",
                print ':',
                print u

if __name__ == "__main__":
    main()

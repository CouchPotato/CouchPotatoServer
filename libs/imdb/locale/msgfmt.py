#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""Generate binary message catalog from textual translation description.

This program converts a textual Uniforum-style message catalog (.po file) into
a binary GNU catalog (.mo file).  This is essentially the same function as the
GNU msgfmt program, however, it is a simpler implementation.

Usage: msgfmt.py [OPTIONS] filename.po

Options:
    -o file
    --output-file=file
        Specify the output file to write to.  If omitted, output will go to a
        file named filename.mo (based off the input file name).

    -h
    --help
        Print this message and exit.

    -V
    --version
        Display version information and exit.

Written by Martin v. Löwis <loewis@informatik.hu-berlin.de>,
refactored / fixed by Thomas Waldmann <tw AT waldmann-edv DOT de>.
"""

import sys, os
import getopt, struct, array

__version__ = "1.3"

class SyntaxErrorException(Exception):
    """raised when having trouble parsing the po file content"""
    pass

class MsgFmt(object):
    """transform .po -> .mo format"""
    def __init__(self):
        self.messages = {}

    def make_filenames(self, filename, outfile=None):
        """Compute .mo name from .po name or language"""
        if filename.endswith('.po'):
            infile = filename
        else:
            infile = filename + '.po'
        if outfile is None:
            outfile = os.path.splitext(infile)[0] + '.mo'
        return infile, outfile

    def add(self, id, str, fuzzy):
        """Add a non-fuzzy translation to the dictionary."""
        if not fuzzy and str:
            self.messages[id] = str

    def read_po(self, lines):
        ID = 1
        STR = 2
        section = None
        fuzzy = False
        line_no = 0
        msgid = msgstr = ''
        # Parse the catalog
        for line in lines:
            line_no += 1
            # If we get a comment line after a msgstr, this is a new entry
            if line.startswith('#') and section == STR:
                self.add(msgid, msgstr, fuzzy)
                section = None
                fuzzy = False
            # Record a fuzzy mark
            if line.startswith('#,') and 'fuzzy' in line:
                fuzzy = True
            # Skip comments
            if line.startswith('#'):
                continue
            # Now we are in a msgid section, output previous section
            if line.startswith('msgid'):
                if section == STR:
                    self.add(msgid, msgstr, fuzzy)
                    fuzzy = False
                section = ID
                line = line[5:]
                msgid = msgstr = ''
            # Now we are in a msgstr section
            elif line.startswith('msgstr'):
                section = STR
                line = line[6:]
            # Skip empty lines
            line = line.strip()
            if not line:
                continue
            # XXX: Does this always follow Python escape semantics?
            line = eval(line)
            if section == ID:
                msgid += line
            elif section == STR:
                msgstr += line
            else:
                raise SyntaxErrorException('Syntax error on line %d, before:\n%s' % (line_no, line))
        # Add last entry
        if section == STR:
            self.add(msgid, msgstr, fuzzy)

    def generate_mo(self):
        """Return the generated output."""
        keys = self.messages.keys()
        # the keys are sorted in the .mo file
        keys.sort()
        offsets = []
        ids = ''
        strs = ''
        for id in keys:
            # For each string, we need size and file offset.  Each string is NUL
            # terminated; the NUL does not count into the size.
            offsets.append((len(ids), len(id), len(strs), len(self.messages[id])))
            ids += id + '\0'
            strs += self.messages[id] + '\0'
        output = []
        # The header is 7 32-bit unsigned integers.  We don't use hash tables, so
        # the keys start right after the index tables.
        # translated string.
        keystart = 7*4 + 16*len(keys)
        # and the values start after the keys
        valuestart = keystart + len(ids)
        koffsets = []
        voffsets = []
        # The string table first has the list of keys, then the list of values.
        # Each entry has first the size of the string, then the file offset.
        for o1, l1, o2, l2 in offsets:
            koffsets += [l1, o1 + keystart]
            voffsets += [l2, o2 + valuestart]
        offsets = koffsets + voffsets
        output.append(struct.pack("Iiiiiii",
                             0x950412deL,       # Magic
                             0,                 # Version
                             len(keys),         # # of entries
                             7*4,               # start of key index
                             7*4 + len(keys)*8, # start of value index
                             0, 0))             # size and offset of hash table
        output.append(array.array("i", offsets).tostring())
        output.append(ids)
        output.append(strs)
        return ''.join(output)


def make(filename, outfile):
    mf = MsgFmt()
    infile, outfile = mf.make_filenames(filename, outfile)
    try:
        lines = file(infile).readlines()
    except IOError, msg:
        print >> sys.stderr, msg
        sys.exit(1)
    try:
        mf.read_po(lines)
        output = mf.generate_mo()
    except SyntaxErrorException, msg:
        print >> sys.stderr, msg

    try:
        open(outfile, "wb").write(output)
    except IOError, msg:
        print >> sys.stderr, msg


def usage(code, msg=''):
    print >> sys.stderr, __doc__
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hVo:', ['help', 'version', 'output-file='])
    except getopt.error, msg:
        usage(1, msg)

    outfile = None
    # parse options
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt in ('-V', '--version'):
            print >> sys.stderr, "msgfmt.py", __version__
            sys.exit(0)
        elif opt in ('-o', '--output-file'):
            outfile = arg
    # do it
    if not args:
        print >> sys.stderr, 'No input file given'
        print >> sys.stderr, "Try `msgfmt --help' for more information."
        return

    for filename in args:
        make(filename, outfile)


if __name__ == '__main__':
    main()


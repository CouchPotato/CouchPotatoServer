# -*- coding: utf-8 -*-
#
#  Copyright 2011 Sybren A. Stüvel <sybren@stuvel.eu>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

'''Utility functions.'''

from __future__ import with_statement

import sys
from optparse import OptionParser

import rsa.key

def private_to_public():
    '''Reads a private key and outputs the corresponding public key.'''

    # Parse the CLI options
    parser = OptionParser(usage='usage: %prog [options]',
            description='Reads a private key and outputs the '
            'corresponding public key. Both private and public keys use '
            'the format described in PKCS#1 v1.5')

    parser.add_option('-i', '--input', dest='infilename', type='string',
            help='Input filename. Reads from stdin if not specified')
    parser.add_option('-o', '--output', dest='outfilename', type='string',
            help='Output filename. Writes to stdout of not specified')

    parser.add_option('--inform', dest='inform',
            help='key format of input - default PEM',
            choices=('PEM', 'DER'), default='PEM')

    parser.add_option('--outform', dest='outform',
            help='key format of output - default PEM',
            choices=('PEM', 'DER'), default='PEM')

    (cli, cli_args) = parser.parse_args(sys.argv)

    # Read the input data
    if cli.infilename:
        print >>sys.stderr, 'Reading private key from %s in %s format' % \
            (cli.infilename, cli.inform)
        with open(cli.infilename) as infile:
            in_data = infile.read()
    else:
        print >>sys.stderr, 'Reading private key from stdin in %s format' % \
            cli.inform
        in_data = sys.stdin.read()


    # Take the public fields and create a public key
    priv_key = rsa.key.PrivateKey.load_pkcs1(in_data, cli.inform)
    pub_key = rsa.key.PublicKey(priv_key.n, priv_key.e)

    # Save to the output file
    out_data = pub_key.save_pkcs1(cli.outform)

    if cli.outfilename:
        print >>sys.stderr, 'Writing public key to %s in %s format' % \
            (cli.outfilename, cli.outform)
        with open(cli.outfilename, 'w') as outfile:
            outfile.write(out_data)
    else:
        print >>sys.stderr, 'Writing public key to stdout in %s format' % \
            cli.outform
        sys.stdout.write(out_data)

    

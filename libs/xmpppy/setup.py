#!/usr/bin/python
# -*- coding: koi8-r -*-
from distutils.core import setup,sys
from setuptools import setup
import os

if sys.version < '2.2.3':
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None

# Set proper release version in source code also!!!
setup(name='xmpppy',
      version='0.5.0rc1',
      author='Alexey Nezhdanov',
      author_email='snakeru@users.sourceforge.net',
      url='http://xmpppy.sourceforge.net/',
      description='XMPP-IM-compliant library for jabber instant messenging.',
      long_description="""This library provides functionality for writing xmpp-compliant
clients, servers and/or components/transports.

It was initially designed as a \"rework\" of the jabberpy library but
has become a separate product.

Unlike jabberpy it is distributed under the terms of GPL.""",
      download_url='http://sourceforge.net/project/showfiles.php?group_id=97081&package_id=103821',
      packages=['xmpp'],
      license="GPL",
      platforms="All",
      keywords=['jabber','xmpp'],
      classifiers = [
          'Topic :: Communications :: Chat',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Natural Language :: English',
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
        ],
     )

import sys
import os
import logging
import unittest
from unittest import TestCase
#from mock import MagicMock

from couchpotato.core.softchroot import SoftChroot

CHROOT_DIR = '/tmp/'

class SoftChrootEnabledTest(TestCase):
    def setUp(self):
        self.b = SoftChroot(CHROOT_DIR)

    def test_enabled(self):
        self.assertTrue( self.b.enabled)

    def test_is_subdir(self):
        self.assertFalse( self.b.is_subdir('') )
        self.assertFalse( self.b.is_subdir(None) )

        self.assertTrue( self.b.is_subdir(CHROOT_DIR) )
        noslash = CHROOT_DIR[:-1]
        self.assertTrue( self.b.is_subdir(noslash) )

        self.assertTrue( self.b.is_subdir(CHROOT_DIR + 'come') )

    def test_is_root_abs(self):
        self.assertFalse( self.b.is_root_abs('') )
        self.assertFalse( self.b.is_root_abs(None) )

        self.assertTrue( self.b.is_root_abs(CHROOT_DIR) )
        noslash = CHROOT_DIR[:-1]
        self.assertTrue( self.b.is_root_abs(noslash) )

        self.assertFalse( self.b.is_root_abs(CHROOT_DIR + 'come') )

    def test_add(self):
        with self.assertRaises(ValueError):
            self.b.add('no_leading_slash')

        self.assertEqual( self.b.add(None), CHROOT_DIR )
        self.assertEqual( self.b.add(''), CHROOT_DIR )

        self.assertEqual( self.b.add('/asdf'), CHROOT_DIR + 'asdf' )

    def test_cut(self):
        with self.assertRaises(ValueError): self.b.cut(None)
        with self.assertRaises(ValueError): self.b.cut('')

        self.assertEqual( self.b.cut(CHROOT_DIR + 'asdf'), '/asdf' )
        self.assertEqual( self.b.cut(CHROOT_DIR), '/' )
        self.assertEqual( self.b.cut(CHROOT_DIR.rstrip(os.path.sep)), '/' )

import sys
import os
import logging
import unittest
from unittest import TestCase

from couchpotato.core.softchroot import SoftChroot

CHROOT_DIR = '/tmp/'

class SoftChrootNonInitialized(TestCase):
    def setUp(self):
        self.b = SoftChroot()

    def test_is_root_abs(self):
        with self.assertRaises(RuntimeError):
            self.b.is_root_abs('1')

    def test_is_subdir(self):
        with self.assertRaises(RuntimeError):
            self.b.is_subdir('1')

    def test_chroot2abs(self):
        with self.assertRaises(RuntimeError):
            self.b.chroot2abs('1')

    def test_abs2chroot(self):
        with self.assertRaises(RuntimeError):
            self.b.abs2chroot('1')

    def test_get_root(self):
        with self.assertRaises(RuntimeError):
            self.b.get_chroot()

class SoftChrootNOTEnabledTest(TestCase):
    def setUp(self):
        self.b = SoftChroot()
        self.b.initialize(None)

    def test_get_root(self):
        with self.assertRaises(RuntimeError):
            self.b.get_chroot()

    def test_chroot2abs_noleading_slash(self):
        path = 'no_leading_slash'
        self.assertEqual( self.b.chroot2abs(path), path )

    def test_chroot2abs(self):
        self.assertIsNone( self.b.chroot2abs(None), None )
        self.assertEqual( self.b.chroot2abs(''), '' )
        self.assertEqual( self.b.chroot2abs('/asdf'), '/asdf' )

    def test_abs2chroot_raise_on_empty(self):
        with self.assertRaises(ValueError):
            self.b.abs2chroot(None)

    def test_abs2chroot(self):
        self.assertEqual( self.b.abs2chroot(''), '' )
        self.assertEqual( self.b.abs2chroot('/asdf'), '/asdf' )
        self.assertEqual( self.b.abs2chroot('/'), '/' )

    def test_get_root(self):
        with self.assertRaises(RuntimeError):
            self.b.get_chroot()

class SoftChrootEnabledTest(TestCase):
    def setUp(self):
        self.b = SoftChroot()
        self.b.initialize(CHROOT_DIR)

    def test_enabled(self):
        self.assertTrue( self.b.enabled)

    def test_is_subdir(self):
        self.assertFalse( self.b.is_subdir('') )
        self.assertFalse( self.b.is_subdir(None) )

        self.assertTrue( self.b.is_subdir(CHROOT_DIR) )
        noslash = CHROOT_DIR[:-1]
        self.assertTrue( self.b.is_subdir(noslash) )

        self.assertTrue( self.b.is_subdir(CHROOT_DIR + 'come') )

    def test_is_root_abs_none(self):
        with self.assertRaises(ValueError):
            self.assertFalse( self.b.is_root_abs(None) )

    def test_is_root_abs(self):
        self.assertFalse( self.b.is_root_abs('') )

        self.assertTrue( self.b.is_root_abs(CHROOT_DIR) )
        noslash = CHROOT_DIR[:-1]
        self.assertTrue( self.b.is_root_abs(noslash) )

        self.assertFalse( self.b.is_root_abs(CHROOT_DIR + 'come') )

    def test_chroot2abs_noleading_slash(self):
        path = 'no_leading_slash'
        path_sl = CHROOT_DIR + path
        #with self.assertRaises(ValueError):
        #    self.b.chroot2abs('no_leading_slash')
        self.assertEqual( self.b.chroot2abs(path), path_sl )

    def test_chroot2abs(self):
        self.assertEqual( self.b.chroot2abs(None), CHROOT_DIR )
        self.assertEqual( self.b.chroot2abs(''), CHROOT_DIR )

        self.assertEqual( self.b.chroot2abs('/asdf'), CHROOT_DIR + 'asdf' )

    def test_abs2chroot_raise_on_empty(self):
        with self.assertRaises(ValueError): self.b.abs2chroot(None)
        with self.assertRaises(ValueError): self.b.abs2chroot('')

    def test_abs2chroot(self):
        self.assertEqual( self.b.abs2chroot(CHROOT_DIR + 'asdf'), '/asdf' )
        self.assertEqual( self.b.abs2chroot(CHROOT_DIR), '/' )
        self.assertEqual( self.b.abs2chroot(CHROOT_DIR.rstrip(os.path.sep)), '/' )

    def test_get_root(self):
        self.assertEqual( self.b.get_chroot(), CHROOT_DIR )

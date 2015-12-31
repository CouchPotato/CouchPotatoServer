import sys
import os
import logging
import unittest
from unittest import TestCase
#from mock import MagicMock

from couchpotato.core.plugins.browser import FileBrowser

CHROOT_DIR = '/tmp/'

class FileBrowserChrootedTest(TestCase):
    def setUp(self):
        self.b = FileBrowser()

        # TODO : remove scrutch:
        self.b.soft_chroot = CHROOT_DIR
        self.b.soft_chroot_enabled = True

        # Logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        # To screen
        hdlr = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%m-%d %H:%M:%S')
        hdlr.setFormatter(formatter)
        #logger.addHandler(hdlr)

    def test_soft_chroot_enabled(self):
        self.assertTrue( self.b.soft_chroot_enabled)

    def test_soft_chroot_is_subdir(self):
        self.assertFalse( self.b.soft_chroot_is_subdir('') )
        self.assertFalse( self.b.soft_chroot_is_subdir(None) )

        self.assertTrue( self.b.soft_chroot_is_subdir(CHROOT_DIR) )
        noslash = CHROOT_DIR[:-1]
        self.assertTrue( self.b.soft_chroot_is_subdir(noslash) )

        self.assertTrue( self.b.soft_chroot_is_subdir(CHROOT_DIR + 'come') )

    def test_soft_chroot_add(self):
        with self.assertRaises(ValueError):
            self.b.soft_chroot_add('no_leading_slash')

        self.assertEqual( self.b.soft_chroot_add(None), CHROOT_DIR )
        self.assertEqual( self.b.soft_chroot_add(''), CHROOT_DIR )

        self.assertEqual( self.b.soft_chroot_add('/asdf'), CHROOT_DIR + 'asdf' )

    def test_soft_chroot_cut(self):
        with self.assertRaises(ValueError): self.b.soft_chroot_cut(None)
        with self.assertRaises(ValueError): self.b.soft_chroot_cut('')

        self.assertEqual( self.b.soft_chroot_cut(CHROOT_DIR + 'asdf'), '/asdf' )
        self.assertEqual( self.b.soft_chroot_cut(CHROOT_DIR), '/' )
        self.assertEqual( self.b.soft_chroot_cut(CHROOT_DIR.rstrip(os.path.sep)), '/' )

    def test_view__chrooted_path_none(self):
        #def view(self, path = '/', show_hidden = True, **kwargs):
        r = self.b.view(None)
        self.assertEqual(r['home'], '/')
        self.assertEqual(r['parent'], '/')
        self.assertTrue(r['is_root'])

    def test_view__chrooted_path_chroot(self):
        #def view(self, path = '/', show_hidden = True, **kwargs):
        for path, parent in [('/asdf','/'), (CHROOT_DIR, '/'), ('/mnk/123/t', '/mnk/123/')]:
            r = self.b.view(path)
            path_strip = path
            if (path.endswith(os.path.sep)):
                path_strip = path_strip.rstrip(os.path.sep)

            self.assertEqual(r['home'], '/')
            self.assertEqual(r['parent'], parent)
            self.assertFalse(r['is_root'])

import sys
import os
import logging
import unittest
from unittest import TestCase
#from mock import MagicMock

from couchpotato.core.plugins.browser import FileBrowser
from couchpotato.core.softchroot import SoftChroot

CHROOT_DIR = '/tmp/'

class FileBrowserChrootedTest(TestCase):
    def setUp(self):
        self.b = FileBrowser()

        # TODO : remove scrutch:
        self.b.soft_chroot = SoftChroot(CHROOT_DIR)

        # Logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        # To screen
        hdlr = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%m-%d %H:%M:%S')
        hdlr.setFormatter(formatter)
        #logger.addHandler(hdlr)

    def test_soft_chroot_enabled(self):
        self.assertTrue( self.b.soft_chroot.enabled)

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

#import sys
import os

import mock
import unittest
from unittest import TestCase


from couchpotato.core.plugins.browser import FileBrowser
from couchpotato.core.softchroot import SoftChroot


CHROOT_DIR = '/tmp/'

# 'couchpotato.core.plugins.browser.Env', 
@mock.patch('couchpotato.core.plugins.browser.Env', name='EnvMock')
class FileBrowserChrootedTest(TestCase):

    def setUp(self):
        self.b = FileBrowser()

    def tuneMock(self, env):
        #set up mock:
        sc = SoftChroot()
        sc.initialize(CHROOT_DIR)
        env.get.return_value = sc


    def test_view__chrooted_path_none(self, env):
        #def view(self, path = '/', show_hidden = True, **kwargs):

        self.tuneMock(env)

        r = self.b.view(None)
        self.assertEqual(r['home'], '/')
        self.assertEqual(r['parent'], '/')
        self.assertTrue(r['is_root'])

    def test_view__chrooted_path_chroot(self, env):
        #def view(self, path = '/', show_hidden = True, **kwargs):

        self.tuneMock(env)

        for path, parent in [('/asdf','/'), (CHROOT_DIR, '/'), ('/mnk/123/t', '/mnk/123/')]:
            r = self.b.view(path)
            path_strip = path
            if (path.endswith(os.path.sep)):
                path_strip = path_strip.rstrip(os.path.sep)

            self.assertEqual(r['home'], '/')
            self.assertEqual(r['parent'], parent)
            self.assertFalse(r['is_root'])

import unittest
from unittest import TestCase
import mock

from couchpotato.environment import Env

class EnvironmentBaseTest(TestCase):
    def test_appname(self):
        self.assertEqual('CouchPotato', Env.get('appname'))

    def test_set_get_appname(self):
        x = 'NEWVALUE'
        Env.set('appname', x)
        self.assertEqual(x, Env.get('appname'))

    def test_get_softchroot(self):
        from couchpotato.core.softchroot import SoftChroot
        sc = Env.get('softchroot')
        self.assertIsInstance(sc, SoftChroot)

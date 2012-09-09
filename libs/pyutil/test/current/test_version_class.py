import unittest

from pyutil import version_class

V = version_class.Version

class T(unittest.TestCase):
    def test_rc_regex_rejects_rc_suffix(self):
        self.failUnlessRaises(ValueError, V, '9.9.9rc9')

    def test_rc_regex_rejects_trailing_garbage(self):
        self.failUnlessRaises(ValueError, V, '9.9.9c9HEYTHISISNTRIGHT')

    def test_comparisons(self):
        self.failUnless(V('1.0') < V('1.1'))
        self.failUnless(V('1.0a1') < V('1.0'))
        self.failUnless(V('1.0a1') < V('1.0b1'))
        self.failUnless(V('1.0b1') < V('1.0c1'))
        self.failUnless(V('1.0a1') < V('1.0a1-r99'))
        self.failUnlessEqual(V('1.0a1.post987'), V('1.0a1-r987'))
        self.failUnlessEqual(str(V('1.0a1.post999')), '1.0.0a1-r999')
        self.failUnlessEqual(str(V('1.0a1-r999')), '1.0.0a1-r999')
        self.failIfEqual(V('1.0a1'), V('1.0a1-r987'))

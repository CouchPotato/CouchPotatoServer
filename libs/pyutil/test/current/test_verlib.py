# -*- coding: utf-8 -*-
"""Tests for distutils.version."""
import unittest
import doctest

from pyutil.verlib import NormalizedVersion as V
from pyutil.verlib import IrrationalVersionError
from pyutil.verlib import suggest_normalized_version as suggest

class VersionTestCase(unittest.TestCase):

    versions = ((V('1.0'), '1.0'),
                (V('1.1'), '1.1'),
                (V('1.2.3'), '1.2.3'),
                (V('1.2'), '1.2'),
                (V('1.2.3a4'), '1.2.3a4'),
                (V('1.2c4'), '1.2c4'),
                (V('1.2.3.4'), '1.2.3.4'),
                (V('1.2.3.4.0b3'), '1.2.3.4b3'),
                (V('1.2.0.0.0'), '1.2'),
                (V('1.0.dev345'), '1.0.dev345'),
                (V('1.0.post456.dev623'), '1.0.post456.dev623'))

    def test_basic_versions(self):

        for v, s in self.versions:
            self.assertEquals(str(v), s)

    def test_from_parts(self):

        for v, s in self.versions:
            v2 = V.from_parts(*v.parts)
            self.assertEquals(v, v2)
            self.assertEquals(str(v), str(v2))

    def test_irrational_versions(self):

        irrational = ('1', '1.2a', '1.2.3b', '1.02', '1.2a03',
                      '1.2a3.04', '1.2.dev.2', '1.2dev', '1.2.dev',
                      '1.2.dev2.post2', '1.2.post2.dev3.post4')

        for s in irrational:
            self.assertRaises(IrrationalVersionError, V, s)

    def test_comparison(self):
        r"""
        >>> V('1.2.0') == '1.2'
        Traceback (most recent call last):
        ...
        TypeError: cannot compare NormalizedVersion and str

        >>> V('1.2.0') == V('1.2')
        True
        >>> V('1.2.0') == V('1.2.3')
        False
        >>> V('1.2.0') < V('1.2.3')
        True
        >>> (V('1.0') > V('1.0b2'))
        True
        >>> (V('1.0') > V('1.0c2') > V('1.0c1') > V('1.0b2') > V('1.0b1')
        ...  > V('1.0a2') > V('1.0a1'))
        True
        >>> (V('1.0.0') > V('1.0.0c2') > V('1.0.0c1') > V('1.0.0b2') > V('1.0.0b1')
        ...  > V('1.0.0a2') > V('1.0.0a1'))
        True

        >>> V('1.0') < V('1.0.post456.dev623')
        True

        >>> V('1.0.post456.dev623') < V('1.0.post456')  < V('1.0.post1234')
        True

        >>> (V('1.0a1')
        ...  < V('1.0a2.dev456')
        ...  < V('1.0a2')
        ...  < V('1.0a2.1.dev456')  # e.g. need to do a quick post release on 1.0a2
        ...  < V('1.0a2.1')
        ...  < V('1.0b1.dev456')
        ...  < V('1.0b2')
        ...  < V('1.0c1.dev456')
        ...  < V('1.0c1')
        ...  < V('1.0.dev7')
        ...  < V('1.0.dev18')
        ...  < V('1.0.dev456')
        ...  < V('1.0.dev1234')
        ...  < V('1.0')
        ...  < V('1.0.post456.dev623')  # development version of a post release
        ...  < V('1.0.post456'))
        True
        """
        # must be a simpler way to call the docstrings
        doctest.run_docstring_examples(self.test_comparison, globals(),
                                       name='test_comparison')

    def test_suggest_normalized_version(self):

        self.assertEquals(suggest('1.0'), '1.0')
        self.assertEquals(suggest('1.0-alpha1'), '1.0a1')
        self.assertEquals(suggest('1.0c2'), '1.0c2')
        self.assertEquals(suggest('walla walla washington'), None)
        self.assertEquals(suggest('2.4c1'), '2.4c1')

        # from setuptools
        self.assertEquals(suggest('0.4a1.r10'), '0.4a1.post10')
        self.assertEquals(suggest('0.7a1dev-r66608'), '0.7a1.dev66608')
        self.assertEquals(suggest('0.6a9.dev-r41475'), '0.6a9.dev41475')
        self.assertEquals(suggest('2.4preview1'), '2.4c1')
        self.assertEquals(suggest('2.4pre1') , '2.4c1')
        self.assertEquals(suggest('2.1-rc2'), '2.1c2')

        # from pypi
        self.assertEquals(suggest('0.1dev'), '0.1.dev0')
        self.assertEquals(suggest('0.1.dev'), '0.1.dev0')

        # we want to be able to parse Twisted
        # development versions are like post releases in Twisted
        self.assertEquals(suggest('9.0.0+r2363'), '9.0.0.post2363')

        # pre-releases are using markers like "pre1"
        self.assertEquals(suggest('9.0.0pre1'), '9.0.0c1')

        # we want to be able to parse Tcl-TK
        # they us "p1" "p2" for post releases
        self.assertEquals(suggest('1.4p1'), '1.4.post1')

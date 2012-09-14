from unittest import TestCase

from pyutil import jsonutil as json

class TestDefault(TestCase):
    def test_default(self):
        self.assertEquals(
            json.dumps(type, default=repr),
            json.dumps(repr(type)))

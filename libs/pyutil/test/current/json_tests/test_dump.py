from unittest import TestCase
from cStringIO import StringIO

from pyutil import jsonutil as json

class TestDump(TestCase):
    def test_dump(self):
        sio = StringIO()
        json.dump({}, sio)
        self.assertEquals(sio.getvalue(), '{}')

    def test_dumps(self):
        self.assertEquals(json.dumps({}), '{}')

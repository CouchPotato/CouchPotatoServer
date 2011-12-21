import unittest

class UnicodeTests(unittest.TestCase):
    """
        Test unicode pathname conversion
    """

    fixtures = [
        (
            'Unicodstring',
            u'Unicodestring'
        ),
    ]

    def testUnicode(self, name, result):
        pass

    def tests(self):
        for (name, result) in self.fixtures:
            self.testUnicode(name, result)



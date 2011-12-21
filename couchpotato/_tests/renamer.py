import unittest

class RenamingTests(unittest.TestCase):
    """
        Test renaming of just downloaded movies
    """

    fixtures = [
        (
            '/path/to/movies/Moviename.2009.720p.bluray-groupname',
            'Unicodestring'
        ),
    ]

    def testUnicode(self, name, result):
        pass

    def tests(self):
        for (name, result) in self.fixtures:
            self.testUnicode(name, result)



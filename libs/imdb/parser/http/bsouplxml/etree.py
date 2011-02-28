"""
parser.http.bsouplxml.etree module (imdb.parser.http package).

This module adapts the beautifulsoup interface to lxml.etree module.

Copyright 2008 H. Turgut Uyar <uyar@tekir.org>
          2008 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import _bsoup as BeautifulSoup
from _bsoup import Tag as Element

import bsoupxpath

# Not directly used by IMDbPY, but do not remove: it's used by IMDbPYKit,
# for example.
def fromstring(xml_string):
    """Return a DOM representation of the string."""
    # We try to not use BeautifulSoup.BeautifulStoneSoup.XML_ENTITIES,
    # for convertEntities.
    return BeautifulSoup.BeautifulStoneSoup(xml_string,
                        convertEntities=None).findChild(True)


def tostring(element, encoding=None, pretty_print=False):
    """Return a string or unicode representation of an element."""
    if encoding is unicode:
        encoding = None
    # For BeautifulSoup 3.1
    #encArgs = {'prettyPrint': pretty_print}
    #if encoding is not None:
    #    encArgs['encoding'] = encoding
    #return element.encode(**encArgs)
    return element.__str__(encoding, pretty_print)

def setattribute(tag, name, value):
    tag[name] = value

def xpath(node, expr):
    """Apply an xpath expression to a node. Return a list of nodes."""
    #path = bsoupxpath.Path(expr)
    path = bsoupxpath.get_path(expr)
    return path.apply(node)


# XXX: monkey patching the beautifulsoup tag class
class _EverythingIsNestable(dict):
    """"Fake that every tag is nestable."""
    def get(self, key, *args, **kwds):
        return []

BeautifulSoup.BeautifulStoneSoup.NESTABLE_TAGS = _EverythingIsNestable()
BeautifulSoup.Tag.tag = property(fget=lambda self: self.name)
BeautifulSoup.Tag.attrib = property(fget=lambda self: self)
BeautifulSoup.Tag.text = property(fget=lambda self: self.string)
BeautifulSoup.Tag.set = setattribute
BeautifulSoup.Tag.getparent = lambda self: self.parent
BeautifulSoup.Tag.drop_tree = BeautifulSoup.Tag.extract
BeautifulSoup.Tag.xpath = xpath

# TODO: setting the text attribute for tags

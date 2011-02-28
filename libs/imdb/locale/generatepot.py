#!/usr/bin/env python
"""
generatepot.py script.

This script generates the imdbpy.pot file, from the DTD.

Copyright 2009 H. Turgut Uyar <uyar@tekir.org>

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

import re
import sys

from datetime import datetime as dt

DEFAULT_MESSAGES = { }

ELEMENT_PATTERN = r"""<!ELEMENT\s+([^\s]+)"""
re_element = re.compile(ELEMENT_PATTERN)

POT_HEADER_TEMPLATE = r"""# Gettext message file for imdbpy
msgid ""
msgstr ""
"Project-Id-Version: imdbpy\n"
"POT-Creation-Date: %(now)s\n"
"PO-Revision-Date: YYYY-MM-DD HH:MM+0000\n"
"Last-Translator: YOUR NAME <YOUR@EMAIL>\n"
"Language-Team: TEAM NAME <TEAM@EMAIL>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=1; plural=0;\n"
"Language-Code: en\n"
"Language-Name: English\n"
"Preferred-Encodings: utf-8\n"
"Domain: imdbpy\n"
"""

if len(sys.argv) != 2:
    print "Usage: %s dtd_file" % sys.argv[0]
    sys.exit()

dtdfilename = sys.argv[1]
dtd = open(dtdfilename).read()
elements = re_element.findall(dtd)
uniq = set(elements)
elements = list(uniq)

print POT_HEADER_TEMPLATE % {
    'now': dt.strftime(dt.now(), "%Y-%m-%d %H:%M+0000")
}
for element in sorted(elements):
    if element in DEFAULT_MESSAGES:
        print '# Default: %s' % DEFAULT_MESSAGES[element]
    else:
        print '# Default: %s' % element.replace('-', ' ').capitalize()
    print 'msgid "%s"' % element
    print 'msgstr ""'
    # use this part instead of the line above to generate the po file for English
    #if element in DEFAULT_MESSAGES:
    #    print 'msgstr "%s"' % DEFAULT_MESSAGES[element]
    #else:
    #    print 'msgstr "%s"' % element.replace('-', ' ').capitalize()
    print


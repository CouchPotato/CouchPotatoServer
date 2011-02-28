"""
parser.http.bsouplxml.html module (imdb.parser.http package).

This module adapts the beautifulsoup interface to lxml.html module.

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


def fromstring(html_string):
    """Return a DOM representation of the string."""
    return BeautifulSoup.BeautifulSoup(html_string,
        convertEntities=BeautifulSoup.BeautifulSoup.HTML_ENTITIES
        ).findChild(True)

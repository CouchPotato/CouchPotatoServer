#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
pyScss, a Scss compiler for Python

@author     German M. Bravo (Kronuz) <german.mb@gmail.com>
@version    1.2.0 alpha
@see        https://github.com/Kronuz/pyScss
@copyright  (c) 2012-2013 German M. Bravo (Kronuz)
@license    MIT License
            http://www.opensource.org/licenses/mit-license.php

pyScss compiles Scss, a superset of CSS that is more powerful, elegant and
easier to maintain than plain-vanilla CSS. The library acts as a CSS source code
preprocesor which allows you to use variables, nested rules, mixins, andhave
inheritance of rules, all with a CSS-compatible syntax which the preprocessor
then compiles to standard CSS.

Scss, as an extension of CSS, helps keep large stylesheets well-organized. It
borrows concepts and functionality from projects such as OOCSS and other similar
frameworks like as Sass. It's build on top of the original PHP xCSS codebase
structure but it's been completely rewritten, many bugs have been fixed and it
has been extensively extended to support almost the full range of Sass' Scss
syntax and functionality.

Bits of code in pyScss come from various projects:
Compass:
    (c) 2009 Christopher M. Eppstein
    http://compass-style.org/
Sass:
    (c) 2006-2009 Hampton Catlin and Nathan Weizenbaum
    http://sass-lang.com/
xCSS:
    (c) 2010 Anton Pawlik
    http://xcss.antpaw.org/docs/

    This file defines Meta data, according to PEP314
    (http://www.python.org/dev/peps/pep-0314/) which is common to both pyScss
    and setup.py distutils.

    We create this here so this information can be compatible with BOTH
    Python 2.x and Python 3.x so setup.py can use it when building pyScss
    for both Py3.x and Py2.x

"""

VERSION_INFO = (1, 2, 0, 'post3')
DATE_INFO = (2013, 10, 8)  # YEAR, MONTH, DAY
VERSION = '.'.join(str(i) for i in VERSION_INFO)
REVISION = '%04d%02d%02d' % DATE_INFO
BUILD_INFO = "pyScss v" + VERSION + " (" + REVISION + ")"
AUTHOR = "German M. Bravo (Kronuz)"
AUTHOR_EMAIL = 'german.mb@gmail.com'
URL = 'http://github.com/Kronuz/pyScss'
DOWNLOAD_URL = 'http://github.com/Kronuz/pyScss/tarball/v' + VERSION
LICENSE = "MIT"
PROJECT = "pyScss"

if __name__ == "__main__":
    print('VERSION      = ' + VERSION)
    print('REVISION     = ' + REVISION)
    print('BUILD_INFO   = ' + BUILD_INFO)
    print('AUTHOR       = ' + AUTHOR)
    print('AUTHOR_EMAIL = ' + AUTHOR_EMAIL)
    print('URL          = ' + URL)
    print('LICENSE      = ' + LICENSE)
    print('PROJECT      = ' + PROJECT)

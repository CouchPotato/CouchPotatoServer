#!/usr/bin/env python
"""
rebuildmo.py script.

This script builds the .mo files, from the .po files.

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

import glob
import msgfmt
import os

#LOCALE_DIR = os.path.dirname(__file__)

def rebuildmo():
    lang_glob = 'imdbpy-*.po'
    created = []
    for input_file in glob.glob(lang_glob):
        lang = input_file[7:-3]
        if not os.path.exists(lang):
            os.mkdir(lang)
        mo_dir = os.path.join(lang, 'LC_MESSAGES')
        if not os.path.exists(mo_dir):
            os.mkdir(mo_dir)
        output_file = os.path.join(mo_dir, 'imdbpy.mo')
        msgfmt.make(input_file, output_file)
        created.append(lang)
    return created


if __name__ == '__main__':
    languages = rebuildmo()
    print 'Created locale for: %s.' % ' '.join(languages)


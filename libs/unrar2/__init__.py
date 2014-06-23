# Copyright (c) 2003-2005 Jimmy Retzlaff, 2008 Konstantin Yegupov
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
pyUnRAR2 is a ctypes based wrapper around the free UnRAR.dll. 

It is an modified version of Jimmy Retzlaff's pyUnRAR - more simple,
stable and foolproof.
Notice that it has INCOMPATIBLE interface.

It enables reading and unpacking of archives created with the
RAR/WinRAR archivers. There is a low-level interface which is very
similar to the C interface provided by UnRAR. There is also a
higher level interface which makes some common operations easier.
"""

__version__ = '0.99.3'

try:
    WindowsError
    in_windows = True
except NameError:
    in_windows = False

if in_windows:
    from windows import RarFileImplementation
else:
    from unix import RarFileImplementation
    
    
import fnmatch, time, weakref

class RarInfo(object):
    """Represents a file header in an archive. Don't instantiate directly.
    Use only to obtain information about file.
    YOU CANNOT EXTRACT FILE CONTENTS USING THIS OBJECT.
    USE METHODS OF RarFile CLASS INSTEAD.

    Properties:
        index - index of file within the archive
        filename - name of the file in the archive including path (if any)
        datetime - file date/time as a struct_time suitable for time.strftime
        isdir - True if the file is a directory
        size - size in bytes of the uncompressed file
        comment - comment associated with the file
        
    Note - this is not currently intended to be a Python file-like object.
    """

    def __init__(self, rarfile, data):
        self.rarfile = weakref.proxy(rarfile)
        self.index = data['index']
        self.filename = data['filename']
        self.isdir = data['isdir']
        self.size = data['size']
        self.datetime = data['datetime']
        self.comment = data['comment']
            


    def __str__(self):
        try :
            arcName = self.rarfile.archiveName
        except ReferenceError:
            arcName = "[ARCHIVE_NO_LONGER_LOADED]"
        return '<RarInfo "%s" in "%s">' % (self.filename, arcName)

class RarFile(RarFileImplementation):

    def __init__(self, archiveName, password=None):
        """Instantiate the archive.

        archiveName is the name of the RAR file.
        password is used to decrypt the files in the archive.

        Properties:
            comment - comment associated with the archive

        >>> print RarFile('test.rar').comment
        This is a test.
        """
        self.archiveName = archiveName
        RarFileImplementation.init(self, password)

    def __del__(self):
        self.destruct()

    def infoiter(self):
        """Iterate over all the files in the archive, generating RarInfos.

        >>> import os
        >>> for fileInArchive in RarFile('test.rar').infoiter():
        ...     print os.path.split(fileInArchive.filename)[-1],
        ...     print fileInArchive.isdir,
        ...     print fileInArchive.size,
        ...     print fileInArchive.comment,
        ...     print tuple(fileInArchive.datetime)[0:5],
        ...     print time.strftime('%a, %d %b %Y %H:%M', fileInArchive.datetime)
        test True 0 None (2003, 6, 30, 1, 59) Mon, 30 Jun 2003 01:59
        test.txt False 20 None (2003, 6, 30, 2, 1) Mon, 30 Jun 2003 02:01
        this.py False 1030 None (2002, 2, 8, 16, 47) Fri, 08 Feb 2002 16:47
        """
        for params in RarFileImplementation.infoiter(self):
            yield RarInfo(self, params)

    def infolist(self):
        """Return a list of RarInfos, descripting the contents of the archive."""
        return list(self.infoiter())

    def read_files(self, condition='*'):
        """Read specific files from archive into memory.
        If "condition" is a list of numbers, then return files which have those positions in infolist.
        If "condition" is a string, then it is treated as a wildcard for names of files to extract.
        If "condition" is a function, it is treated as a callback function, which accepts a RarInfo object 
            and returns boolean True (extract) or False (skip).
        If "condition" is omitted, all files are returned.
        
        Returns list of tuples (RarInfo info, str contents)
        """
        checker = condition2checker(condition)
        return RarFileImplementation.read_files(self, checker)
        

    def extract(self,  condition='*', path='.', withSubpath=True, overwrite=True):
        """Extract specific files from archive to disk.
        
        If "condition" is a list of numbers, then extract files which have those positions in infolist.
        If "condition" is a string, then it is treated as a wildcard for names of files to extract.
        If "condition" is a function, it is treated as a callback function, which accepts a RarInfo object
            and returns either boolean True (extract) or boolean False (skip).
        DEPRECATED: If "condition" callback returns string (only supported for Windows) - 
            that string will be used as a new name to save the file under.
        If "condition" is omitted, all files are extracted.
        
        "path" is a directory to extract to
        "withSubpath" flag denotes whether files are extracted with their full path in the archive.
        "overwrite" flag denotes whether extracted files will overwrite old ones. Defaults to true.
        
        Returns list of RarInfos for extracted files."""
        checker = condition2checker(condition)
        return RarFileImplementation.extract(self, checker, path, withSubpath, overwrite)

def condition2checker(condition):
    """Converts different condition types to callback"""
    if type(condition) in [str, unicode]:
        def smatcher(info):
            return fnmatch.fnmatch(info.filename, condition)
        return smatcher
    elif type(condition) in [list, tuple] and type(condition[0]) in [int, long]:
        def imatcher(info):
            return info.index in condition
        return imatcher
    elif callable(condition):
        return condition
    else:
        raise TypeError



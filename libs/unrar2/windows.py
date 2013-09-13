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

# Low level interface - see UnRARDLL\UNRARDLL.TXT

from __future__ import generators

import ctypes, ctypes.wintypes
import os, os.path, sys
import Queue
import time

from rar_exceptions import *

ERAR_END_ARCHIVE = 10
ERAR_NO_MEMORY = 11
ERAR_BAD_DATA = 12
ERAR_BAD_ARCHIVE = 13
ERAR_UNKNOWN_FORMAT = 14
ERAR_EOPEN = 15
ERAR_ECREATE = 16
ERAR_ECLOSE = 17
ERAR_EREAD = 18
ERAR_EWRITE = 19
ERAR_SMALL_BUF = 20
ERAR_UNKNOWN = 21

RAR_OM_LIST = 0
RAR_OM_EXTRACT = 1

RAR_SKIP = 0
RAR_TEST = 1
RAR_EXTRACT = 2

RAR_VOL_ASK = 0
RAR_VOL_NOTIFY = 1

RAR_DLL_VERSION = 3

# enum UNRARCALLBACK_MESSAGES
UCM_CHANGEVOLUME = 0
UCM_PROCESSDATA = 1
UCM_NEEDPASSWORD = 2

architecture_bits = ctypes.sizeof(ctypes.c_voidp)*8
dll_name = "unrar.dll"
if architecture_bits == 64:
    dll_name = "x64\\unrar64.dll"
    
    
try:
    unrar = ctypes.WinDLL(os.path.join(os.path.split(__file__)[0], 'UnRARDLL', dll_name))
except WindowsError:
    unrar = ctypes.WinDLL(dll_name)


class RAROpenArchiveDataEx(ctypes.Structure):
    def __init__(self, ArcName=None, ArcNameW=u'', OpenMode=RAR_OM_LIST):
        self.CmtBuf = ctypes.c_buffer(64*1024)
        ctypes.Structure.__init__(self, ArcName=ArcName, ArcNameW=ArcNameW, OpenMode=OpenMode, _CmtBuf=ctypes.addressof(self.CmtBuf), CmtBufSize=ctypes.sizeof(self.CmtBuf))

    _fields_ = [
                ('ArcName', ctypes.c_char_p),
                ('ArcNameW', ctypes.c_wchar_p),
                ('OpenMode', ctypes.c_uint),
                ('OpenResult', ctypes.c_uint),
                ('_CmtBuf', ctypes.c_voidp),
                ('CmtBufSize', ctypes.c_uint),
                ('CmtSize', ctypes.c_uint),
                ('CmtState', ctypes.c_uint),
                ('Flags', ctypes.c_uint),
                ('Reserved', ctypes.c_uint*32),
               ]

class RARHeaderDataEx(ctypes.Structure):
    def __init__(self):
        self.CmtBuf = ctypes.c_buffer(64*1024)
        ctypes.Structure.__init__(self, _CmtBuf=ctypes.addressof(self.CmtBuf), CmtBufSize=ctypes.sizeof(self.CmtBuf))

    _fields_ = [
                ('ArcName', ctypes.c_char*1024),
                ('ArcNameW', ctypes.c_wchar*1024),
                ('FileName', ctypes.c_char*1024),
                ('FileNameW', ctypes.c_wchar*1024),
                ('Flags', ctypes.c_uint),
                ('PackSize', ctypes.c_uint),
                ('PackSizeHigh', ctypes.c_uint),
                ('UnpSize', ctypes.c_uint),
                ('UnpSizeHigh', ctypes.c_uint),
                ('HostOS', ctypes.c_uint),
                ('FileCRC', ctypes.c_uint),
                ('FileTime', ctypes.c_uint),
                ('UnpVer', ctypes.c_uint),
                ('Method', ctypes.c_uint),
                ('FileAttr', ctypes.c_uint),
                ('_CmtBuf', ctypes.c_voidp),
                ('CmtBufSize', ctypes.c_uint),
                ('CmtSize', ctypes.c_uint),
                ('CmtState', ctypes.c_uint),
                ('Reserved', ctypes.c_uint*1024),
               ]

def DosDateTimeToTimeTuple(dosDateTime):
    """Convert an MS-DOS format date time to a Python time tuple.
    """
    dosDate = dosDateTime >> 16
    dosTime = dosDateTime & 0xffff
    day = dosDate & 0x1f
    month = (dosDate >> 5) & 0xf
    year = 1980 + (dosDate >> 9)
    second = 2*(dosTime & 0x1f)
    minute = (dosTime >> 5) & 0x3f
    hour = dosTime >> 11
    return time.localtime(time.mktime((year, month, day, hour, minute, second, 0, 1, -1)))

def _wrap(restype, function, argtypes):
    result = function
    result.argtypes = argtypes
    result.restype = restype
    return result

RARGetDllVersion = _wrap(ctypes.c_int, unrar.RARGetDllVersion, [])

RAROpenArchiveEx = _wrap(ctypes.wintypes.HANDLE, unrar.RAROpenArchiveEx, [ctypes.POINTER(RAROpenArchiveDataEx)])

RARReadHeaderEx = _wrap(ctypes.c_int, unrar.RARReadHeaderEx, [ctypes.wintypes.HANDLE, ctypes.POINTER(RARHeaderDataEx)])

_RARSetPassword = _wrap(ctypes.c_int, unrar.RARSetPassword, [ctypes.wintypes.HANDLE, ctypes.c_char_p])
def RARSetPassword(*args, **kwargs):
    _RARSetPassword(*args, **kwargs)

RARProcessFile = _wrap(ctypes.c_int, unrar.RARProcessFile, [ctypes.wintypes.HANDLE, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p])

RARCloseArchive = _wrap(ctypes.c_int, unrar.RARCloseArchive, [ctypes.wintypes.HANDLE])

UNRARCALLBACK = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint, ctypes.c_long, ctypes.c_long, ctypes.c_long)
RARSetCallback = _wrap(ctypes.c_int, unrar.RARSetCallback, [ctypes.wintypes.HANDLE, UNRARCALLBACK, ctypes.c_long])



RARExceptions = {
                 ERAR_NO_MEMORY : MemoryError,
                 ERAR_BAD_DATA : ArchiveHeaderBroken,
                 ERAR_BAD_ARCHIVE : InvalidRARArchive,
                 ERAR_EOPEN : FileOpenError,
                }

class PassiveReader:
    """Used for reading files to memory"""
    def __init__(self, usercallback = None):
        self.buf = []
        self.ucb = usercallback
    
    def _callback(self, msg, UserData, P1, P2):
        if msg == UCM_PROCESSDATA:
            data = (ctypes.c_char*P2).from_address(P1).raw
            if self.ucb!=None:
                self.ucb(data)
            else:
                self.buf.append(data)
        return 1
    
    def get_result(self):
        return ''.join(self.buf)

class RarInfoIterator(object):
    def __init__(self, arc):
        self.arc = arc
        self.index = 0
        self.headerData = RARHeaderDataEx()
        self.res = RARReadHeaderEx(self.arc._handle, ctypes.byref(self.headerData))
        if self.res==ERAR_BAD_DATA:
            raise IncorrectRARPassword
        self.arc.lockStatus = "locked"
        self.arc.needskip = False
        
    def __iter__(self):
        return self
        
    def next(self):
        if self.index>0:
            if self.arc.needskip:
                RARProcessFile(self.arc._handle, RAR_SKIP, None, None)
            self.res = RARReadHeaderEx(self.arc._handle, ctypes.byref(self.headerData))

        if self.res:
            raise StopIteration 
        self.arc.needskip = True
        
        data = {}
        data['index'] = self.index
        data['filename'] = self.headerData.FileName
        data['datetime'] = DosDateTimeToTimeTuple(self.headerData.FileTime)
        data['isdir'] = ((self.headerData.Flags & 0xE0) == 0xE0)
        data['size'] = self.headerData.UnpSize + (self.headerData.UnpSizeHigh << 32)
        if self.headerData.CmtState == 1:
            data['comment'] = self.headerData.CmtBuf.value
        else:
            data['comment'] = None
        self.index += 1
        return data

            
    def __del__(self):
        self.arc.lockStatus = "finished"

def generate_password_provider(password):
    def password_provider_callback(msg, UserData, P1, P2):
        if msg == UCM_NEEDPASSWORD and password!=None:
            (ctypes.c_char*P2).from_address(P1).value = password
        return 1
    return password_provider_callback

class RarFileImplementation(object):

    def init(self, password=None):
        self.password = password
        archiveData = RAROpenArchiveDataEx(ArcNameW=self.archiveName, OpenMode=RAR_OM_EXTRACT)
        self._handle = RAROpenArchiveEx(ctypes.byref(archiveData))
        self.c_callback = UNRARCALLBACK(generate_password_provider(self.password))
        RARSetCallback(self._handle, self.c_callback, 1)

        if archiveData.OpenResult != 0:
            raise RARExceptions[archiveData.OpenResult]

        if archiveData.CmtState == 1:
            self.comment = archiveData.CmtBuf.value
        else:
            self.comment = None

        if password:
            RARSetPassword(self._handle, password)
            
        self.lockStatus = "ready"
            


    def destruct(self):
        if self._handle and RARCloseArchive:
            RARCloseArchive(self._handle)

    def make_sure_ready(self):
        if self.lockStatus == "locked":
            raise InvalidRARArchiveUsage("cannot execute infoiter() without finishing previous one")
        if self.lockStatus == "finished":
            self.destruct()
            self.init(self.password)

    def infoiter(self):
        self.make_sure_ready()
        return RarInfoIterator(self)

    def read_files(self, checker):
        res = []
        for info in self.infoiter():
            if checker(info) and not info.isdir:
                reader = PassiveReader()
                c_callback = UNRARCALLBACK(reader._callback)
                RARSetCallback(self._handle, c_callback, 1)
                tmpres = RARProcessFile(self._handle, RAR_TEST, None, None)
                if tmpres==ERAR_BAD_DATA:
                    raise IncorrectRARPassword
                self.needskip = False
                res.append((info, reader.get_result()))
        return res
        

    def extract(self,  checker, path, withSubpath, overwrite):
        res = []
        for info in self.infoiter():
            checkres = checker(info)
            if checkres!=False and not info.isdir:
                if checkres==True:
                    fn = info.filename
                    if not withSubpath:
                        fn = os.path.split(fn)[-1]
                    target = os.path.join(path, fn)
                else:
                    raise DeprecationWarning, "Condition callbacks returning strings are deprecated and only supported in Windows"                    
                    target = checkres
                if overwrite or (not os.path.exists(target)):
                    tmpres = RARProcessFile(self._handle, RAR_EXTRACT, None, target)
                    if tmpres==ERAR_BAD_DATA:
                        raise IncorrectRARPassword

                self.needskip = False
                res.append(info)
        return res



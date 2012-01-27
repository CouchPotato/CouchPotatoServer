from ctypes import *
from ctypes.wintypes import *
import win32process


class PROCESSENTRY32(Structure):
    _fields_ = (
        ('dwSize', DWORD,),
        ('cntUsage', DWORD,),
        ('th32ProcessID', DWORD,),
        ('th32DefaultHeapID', POINTER(ULONG),),
        ('th32ModuleID', DWORD,),
        ('cntThreads', DWORD,),
        ('th32ParentProcessID', DWORD,),
        ('pcPriClassBase', LONG,),
        ('dwFlags', DWORD,),
        ('szExeFile', c_char * MAX_PATH,),
        )


def getppid(pid):
    """the Windows version of os.getppid"""
    pe = PROCESSENTRY32()
    pe.dwSize = sizeof(PROCESSENTRY32)

    snapshot = windll.kernel32.CreateToolhelp32Snapshot(2, 0)
    try:
        if not windll.kernel32.Process32First(snapshot, byref(pe)):
            raise WindowsError
        while pe.th32ProcessID != pid:
            if not windll.kernel32.Process32Next(snapshot, byref(pe)):
                raise WindowsError
        result = pe.th32ParentProcessID
    finally:
        windll.kernel32.CloseHandle(snapshot)

    if result not in win32process.EnumProcesses():
        result = 1

    return result


import os
if not hasattr(os, 'getppid'):
    os.getppid = getppid

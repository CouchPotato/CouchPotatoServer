from couchpotato.api import addApiView
from couchpotato.core.helpers.request import getParam, jsonified
from couchpotato.core.helpers.variable import getUserDir
from couchpotato.core.plugins.base import Plugin
import ctypes
import os
import string

if os.name == 'nt':
    import imp
    try:
        imp.find_module('win32file')
    except:
        # todo:: subclass ImportError for missing dependencies, vs. broken plugins?
        raise ImportError("Missing the win32file module, which is a part of the prerequisite \
            pywin32 package. You can get it from http://sourceforge.net/projects/pywin32/files/pywin32/");
    else:
        import win32file

class FileBrowser(Plugin):

    def __init__(self):
        addApiView('directory.list', self.view, docs = {
            'desc': 'Return the directory list of a given directory',
            'params': {
                'path': {'desc': 'The directory to scan'},
                'show_hidden': {'desc': 'Also show hidden files'}
            },
            'return': {'type': 'object', 'example': """{
    'is_root': bool, //is top most folder
    'parent': string, //parent folder of requested path
    'home': string, //user home folder
    'empty': bool, //directory is empty
    'dirs': array, //directory names
}"""}
        })

    def getDirectories(self, path = '/', show_hidden = True):

        # Return driveletters or root if path is empty
        if path == '/' or not path or path == '\\':
            if os.name == 'nt':
                return self.getDriveLetters()
            path = '/'

        dirs = []
        for f in os.listdir(path):
            p = os.path.join(path, f)
            if os.path.isdir(p) and ((self.is_hidden(p) and bool(int(show_hidden))) or not self.is_hidden(p)):
                dirs.append(p + os.path.sep)

        return sorted(dirs)

    def getFiles(self):
        pass

    def getDriveLetters(self):

        driveletters = []
        for drive in string.ascii_uppercase:
            if win32file.GetDriveType(drive + ":") in [win32file.DRIVE_FIXED, win32file.DRIVE_REMOTE, win32file.DRIVE_RAMDISK, win32file.DRIVE_REMOVABLE]:
                driveletters.append(drive + ":\\")

        return driveletters

    def view(self):

        path = getParam('path', '/')
        home = getUserDir()

        if not path:
            path = home

        try:
            dirs = self.getDirectories(path = path, show_hidden = getParam('show_hidden', True))
        except:
            dirs = []

        parent = os.path.dirname(path.rstrip(os.path.sep))
        if parent == path.rstrip(os.path.sep):
            parent = '/'
        elif parent != '/' and parent[-2:] != ':\\':
            parent += os.path.sep

        return jsonified({
            'is_root': path == '/',
            'empty': len(dirs) == 0,
            'parent': parent,
            'home': home + os.path.sep,
            'platform': os.name,
            'dirs': dirs,
        })


    def is_hidden(self, filepath):
        name = os.path.basename(os.path.abspath(filepath))
        return name.startswith('.') or self.has_hidden_attribute(filepath)

    def has_hidden_attribute(self, filepath):
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(unicode(filepath))
            assert attrs != -1
            result = bool(attrs & 2)
        except (AttributeError, AssertionError):
            result = False
        return result

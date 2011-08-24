from couchpotato.api import addApiView
from couchpotato.core.helpers.request import getParam, jsonified
from couchpotato.core.plugins.base import Plugin
import os
import string

if os.name == 'nt':
    import win32file

class FileBrowser(Plugin):

    def __init__(self):
        addApiView('directory.list', self.view)

    def getDirectories(self, path = '/', show_hidden = True):

        # Return driveletters or root if path is empty
        if path == '/' or not path:
            if os.name == 'nt':
                return self.getDriveLetters()
            path = '/'

        dirs = []
        for f in os.listdir(path):
            p = os.path.join(path, f)
            if(os.path.isdir(p)):
                dirs.append(p + '/')

        return dirs

    def getFiles(self):
        pass

    def getDriveLetters(self):

        driveletters = []
        for drive in string.ascii_uppercase:
            if win32file.GetDriveType(drive + ":") == win32file.DRIVE_FIXED:
                driveletters.append(drive + ":")

        return driveletters

    def view(self):

        try:
            dirs = self.getDirectories(path = getParam('path', '/'), show_hidden = getParam('show_hidden', True))
        except:
            dirs = []

        return jsonified({
            'empty': len(dirs) == 0,
            'dirs': dirs,
        })
